use pyo3::prelude::*;
use external_sort::{ExternalSorter, ExternallySortable};
use itertools::Itertools;
use std::cmp::Ordering;
use std::io::{BufRead, BufReader, Read, Seek, Write};
use std::iter::Peekable;
use std::path::PathBuf;
use std::str::Chars;
use serde::{Deserialize, Serialize};


// Define a string structure that can be sorted externally
#[derive(Serialize, Deserialize, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct TsvLine {
    the_line: String,
}

impl TsvLine {
    fn new(line: &str) -> TsvLine {
        TsvLine { the_line: line.to_string() }
    }
}

impl ExternallySortable for TsvLine {
    fn get_size(&self) -> u64 {
        self.the_line.len() as u64
    }
}


#[pyfunction]
fn linecomp(l1: &str, l2: &str) -> i8 {
    match tsv_cmp(l1, l2) {
        Ordering::Less => -1,
        Ordering::Equal => 0,
        Ordering::Greater => 1,
    }
}

#[pyfunction]
fn sort_lines(lines: Vec<String>) -> Vec<String> {
    let mut lines = lines;
    lines.sort_by(|a, b| tsv_cmp(a, b));
    lines
}

// This is the end marker for an SQL COPY stream:
const SQL_COPY_END: &str = "\\.";

/// Merge sort a range of lines from an input file and write the result to another file.
///
/// The function `sort_file_lines` seeks to the given start position in the input file, reads
/// lines until the end marker is reached, does an external sort of lines using `ExternalSorter`
/// from the `external_sort` crate and the `tsv_cmp` function below, and writes the sorted lines to
/// the output file.
///
/// # Arguments
///
/// * `input` - The input file to read lines from.
/// * `output` - The output file to write sorted lines to.
/// * `start` - The start position in the input file.
/// * `end` - The characters of a line that marks the end of the range.
///
/// # Returns
///
/// The function returns the number of lines read and written.
///
/// # Errors
///
/// The function returns an error if the input file cannot be read or the output file cannot be
/// written.
///
/// # Examples
///
/// ```no_run
/// use pgtricks::sort_file_lines;
///
/// let input = "input.txt";
/// let output = "output.txt";
/// let start = 0;
/// let end = "END";
/// let result = sort_file_lines(input, output, start, end);
/// assert!(result.is_ok());
/// ```
///
#[pyfunction]
fn sort_file_lines(input: PathBuf, output: PathBuf, start: u64) -> PyResult<u64> {
    // Open the input file and seek to the start position
    let mut input_file = std::fs::File::open(input)?;
    input_file.seek(std::io::SeekFrom::Start(start))?;
    // Wrap the input file in a buffered reader
    let mut input = BufReader::new(&mut input_file);
    // Create an iterator which reads lines until the end marker and doesn't consume the end marker
    let mut binding = input.by_ref().lines().peekable();
    let lines = binding
        .peeking_take_while(|line| line.as_ref().map(|l| l != SQL_COPY_END).unwrap_or(false))
        .map(|line| TsvLine::new(&line.unwrap()));
    // Do the external sort
    let iter = ExternalSorter::new(1000000, None).sort_by(
        lines,
        |a, b| tsv_cmp(a.the_line.as_str(), b.the_line.as_str()),
    ).unwrap();
    // Append the sorted lines to the output file
    let output_file = std::fs::OpenOptions::new().write(true).append(true).open(output)?;
    let mut output = std::io::BufWriter::new(output_file);
    for line in iter {
        writeln!(output, "{}", line.unwrap().the_line)?;
    }
    // Write the end marker (which was not consumed by peeking_take_while)
    writeln!(output, "{}", binding.next().unwrap().unwrap())?;
    // return the stream position from the counting reader object
    Ok(input.stream_position().unwrap())
}

/// A Python module implemented in Rust.
#[pymodule]
#[pyo3(name = "_tsv_sort")]
fn tsv_sort(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(linecomp, m)?)?;
    m.add_function(wrap_pyfunction!(sort_lines, m)?)?;
    m.add_function(wrap_pyfunction!(sort_file_lines, m)?)?;
    Ok(())
}

/// Compare two tab-delimited lines lexicographically, treating numbers as numbers.
///
/// The function `tsv_cmp` compares two tab-delimited lines lexicographically, treating
/// numbers as numbers. The implementation is optimized for speed and consistent sorting, not a
/// fully logical sorting order.
///
/// The comparison is done field by field, and the fields are compared as follows:
///
/// 1. If the field is identical on both lines, move on to the next field.
/// 2. If both fields start with a negative sign, the comparison of the remainder of the fields is
///    inverted.
/// 3. If only one field starts with a negative sign, the field with the negative sign is considered
///    smaller, even if the rest of the content is not numeric.
/// 6. Leading zeros are skipped.
/// 7. If one of the fields has more remaining digits before the first non-digit or field end, it is
///    considered larger.
/// 8. If both fields have the same number of initial non-leading-zero digits, the one whose
///    earliest digit is larger is considered larger.
/// 8. After initial identical digits, comparison continues character by character until field end.
/// 9. If there's a decimal point at the same position in both fields, comparison continues after
///    them character by character. The first differing character determines the comparison result.
/// 10. If one of the fields has extra characters, it is considered larger.
///     This means that we consider e.g. 123.00 > 123.0 (which is fine for our purposes)
///
/// # Arguments
///
/// * `l1` - The first line to compare.
/// * `l2` - The second line to compare.
///
/// # Returns
///
/// The function returns an `Ordering` value, which is one of `Less`, `Equal`, or `Greater`.
///
/// # Examples
///
/// ```
/// use pgtricks::tsv_cmp;
/// use std::cmp::Ordering;
///
/// assert_eq!(tsv_cmp("123", "123"), Ordering::Equal);
/// assert_eq!(tsv_cmp("123", "124"), Ordering::Less);
/// assert_eq!(tsv_cmp("124", "123"), Ordering::Greater);
/// assert_eq!(tsv_cmp("123\tour", "123\town"), Ordering::Less);
///
pub fn tsv_cmp(l1: &str, l2: &str) -> Ordering {
    let mut l1_chars = l1.chars().peekable();
    let mut l2_chars = l2.chars().peekable();
    let mut l1_larger;

    'next_field: loop {
        // handle negative prefixes and end of lines
        l1_larger = Ordering::Greater;  // reset negative prefix status for each new field
        match (l1_chars.peek(), l2_chars.peek()) {
            (Some(_), None) => return Ordering::Greater,  // end of line for l2, so l1 > l2
            (None, Some(_)) => return Ordering::Less,  // end of line for l1, so l1 < l2
            (None, None) => return Ordering::Equal,  // end of both lines, so l1 == l2
            (Some('-'), Some('-')) => {  // both l1 and l2 have negative prefixes
                l1_larger = Ordering::Less;  // invert the comparison of absolute values
                // skip the negative prefixes and start comparing absolute values
                l1_chars.next();
                l2_chars.next();
            }
            (Some('-'), Some(_)) => {  // only l1 has a negative prefix, so l1 < l2
                return Ordering::Less;
            }
            (Some(_), Some('-')) => {  // only l2 has a negative prefix, so l1 > l2
                return Ordering::Greater;
            }
            (Some(_), Some(_)) => {}  // neither has a negative prefix, continue
        }

        skip_leading_zeros(&mut l1_chars);
        skip_leading_zeros(&mut l2_chars);

        let mut integer_order = Ordering::Equal;
        loop {
            match (l1_chars.next(), l2_chars.next()) {
                (Some(_), None) => {  // end of line for l2
                    return integer_order.then(l1_larger);  // so |l1| > |l2| unless digits differed
                }
                (None, Some(_)) => {  // end of line for l1
                    return match integer_order {
                        Ordering::Less => l1_larger.reverse(),  // by digits |l1| < |l2| anyway
                        Ordering::Equal => l1_larger.reverse(),  // by convention, longer is larger
                        Ordering::Greater => l1_larger,  // but digits differed and |l1| > |l2|
                    };
                }
                (None, None) => {  // end of both lines, result depends on digit comparison
                    return match integer_order {
                        Ordering::Less => l1_larger.reverse(),
                        Ordering::Equal => Ordering::Equal,
                        Ordering::Greater => l1_larger,
                    };
                }
                (Some(c1), Some(c2)) => {
                    if !c1.is_ascii_digit() {
                        if c2.is_ascii_digit() {  // l1 has a non-digit character, l2 has a digit
                            return l1_larger.reverse();  // so l2 is longer, thus |l1| < |l2|
                        };
                        // both l1 and l2 have a non-digit character after the same number of digits
                        // so the result depends on digit comparisons before the non-digit character
                        match integer_order {
                            // non-equal comparison before the non-digit character
                            Ordering::Less => return l1_larger.reverse(),
                            Ordering::Greater => return l1_larger,
                            Ordering::Equal => {
                                // l1 and l2 have the same digits until the non-digit character
                                if c1 == '.' {
                                    if c2 == '.' {
                                        // it was a decimal point in both, and as both have the same
                                        // integer part, now compare the fractional parts
                                        break;
                                    }
                                    return l1_larger;  // l1 has fraction, l2 not, so |l1| > |l2|
                                }
                                if c2 == '.' {
                                    return l1_larger.reverse();  // l2 has, l1 not, so |l1| < |l2|
                                }
                                // both l1 and l2 have a non-digit character, and it's not a
                                // decimal, so we shift to non-numeric comparison below
                            }
                        }
                    } else if !c2.is_ascii_digit() {
                        return l1_larger;  // l2 has a non-digit, l1 a digit, so |l1| > |l2|
                    }
                    // compare the next characters in l1 and l2, digit or not
                    if integer_order.is_eq() {  // all characters so far have been equal
                        integer_order = c1.cmp(&c2);  // so compare the current characters
                        // note: we don't draw any conclusions yet, as we don't know if the number
                        // of digits is the same in both lines
                    }
                }
            }
        }

        // l1 and l2 have the same integer part, compare the fractional part
        loop {
            match (l1_chars.next(), l2_chars.next()) {
                (Some(_), None) => return l1_larger,  // end of line for l2, so |l1| > |l2|
                (None, Some(_)) => return l1_larger.reverse(),  // EOL for l1, so |l1| < |l2|
                (None, None) => return Ordering::Equal,  // end of both lines, so l1 == l2
                (Some(c1), Some(c2)) => {
                    if c1 == '\t' {  // field ends in l1
                        if c2 == '\t' {  // field ends in l2, too
                            // l1 and l2 have the same fractional part, they are equal
                            continue 'next_field;
                        }
                        // l1 has fewer fractional digits than l2, so |l1| < |l2|
                        return l1_larger.reverse();
                    }
                    if c2 == '\t' {  // field ends in l2
                        // l1 has more fractional digits than l2, so |l1| > |l2|
                        return l1_larger;
                    }
                    match c1.cmp(&c2) {
                        Ordering::Less => return l1_larger.reverse(),
                        Ordering::Greater => return l1_larger,
                        Ordering::Equal => continue,
                    }
                }
            }
        }
    }
}


fn skip_leading_zeros(field_chars: &mut Peekable<Chars>) {
    while let Some(c) = field_chars.peek() {
        if *c == '0' {
            field_chars.next();
        } else {
            break;
        }
    }
}

#[cfg(test)]
#[macro_use]
extern crate rstest;

#[cfg(test)]
mod tests {
    use super::*;

    #[rstest]
    // integers, equal length
    #[case("123", "123", Ordering::Equal)]
    #[case("123", "124", Ordering::Less)]
    #[case("124", "123", Ordering::Greater)]
    // integers, different length
    #[case("123", "1234", Ordering::Less)]
    #[case("1234", "123", Ordering::Greater)]
    // negative integers
    #[case("-123", "123", Ordering::Less)]
    #[case("123", "-123", Ordering::Greater)]
    #[case("-123", "-123", Ordering::Equal)]
    #[case("-123", "-124", Ordering::Greater)]
    #[case("-124", "-123", Ordering::Less)]
    // integers vs. floats
    #[case("123", "122.9", Ordering::Greater)]
    #[case("123", "123.0", Ordering::Less)] // by convention, shorter notation is less than longer
    #[case("123", "123.1", Ordering::Less)]
    #[case("123.1", "123", Ordering::Greater)]
    #[case("123.0", "123", Ordering::Greater)] // by convention, shorter notation is less than longer
    #[case("122.9", "123", Ordering::Less)]
    // floats vs. floats, equal length, same integer part
    #[case("123.1", "123.1", Ordering::Equal)]
    #[case("123.0", "123.1", Ordering::Less)]
    #[case("123.1", "123.0", Ordering::Greater)]
    // floats vs. floats, different length, same integer part
    #[case("123.0", "123.01", Ordering::Less)]
    #[case("123.01", "123.0", Ordering::Greater)]
    #[case("123.0", "123.00", Ordering::Less)] // by convention, shorter notation less than longer
    #[case("123.00", "123.0", Ordering::Greater)] // by convention, shorter notation less than longer-
    // floats vs. floats, same length, different integer part
    #[case("123.0", "124.0", Ordering::Less)]
    #[case("124.0", "123.0", Ordering::Greater)]
    #[case("123.0", "124.1", Ordering::Less)]
    #[case("124.1", "123.0", Ordering::Greater)]
    // floats vs. floats, different length, different integer part
    #[case("123.0", "124.00", Ordering::Less)]
    #[case("124.00", "123.0", Ordering::Greater)]
    #[case("123.0", "124.01", Ordering::Less)]
    #[case("124.01", "123.0", Ordering::Greater)]
    // negative floats
    #[case("-123.0", "123.0", Ordering::Less)]
    #[case("123.0", "-123.0", Ordering::Greater)]
    #[case("-123.0", "-123.0", Ordering::Equal)]
    #[case("-123.0", "-123.1", Ordering::Greater)]
    #[case("-123.1", "-123.0", Ordering::Less)]
    #[case("-123.0", "-123.00", Ordering::Greater)] // by convention, shorter notation less than long
    #[case("-123.00", "-123.0", Ordering::Less)] // by convention, shorter notation less than long
    #[case("-123.02", "-123.01", Ordering::Less)]
    #[case("-123.01", "-123.02", Ordering::Greater)]
    #[case("-123.00", "-123.01", Ordering::Greater)]
    #[case("-123.01", "-123.00", Ordering::Less)]
    #[case("-123.0", "-123.01", Ordering::Greater)]
    #[case("-123.01", "-123.0", Ordering::Less)]
    #[case("-123.0", "-124.0", Ordering::Greater)]
    #[case("-124.0", "-123.0", Ordering::Less)]
    #[case("-123.0", "-124.1", Ordering::Greater)]
    #[case("-124.1", "-123.0", Ordering::Less)]
    #[case("-123.0", "-124.00", Ordering::Greater)]
    #[case("-124.00", "-123.0", Ordering::Less)]
    #[case("-123.0", "-124.01", Ordering::Greater)]
    #[case("-124.01", "-123.0", Ordering::Less)]
    // negative integers vs. floats
    #[case("-123", "123.0", Ordering::Less)]
    #[case("123", "-123.0", Ordering::Greater)]
    #[case("-123.0", "123", Ordering::Less)]
    #[case("123.0", "-123", Ordering::Greater)]
    #[case("-123", "123.1", Ordering::Less)]
    #[case("123.1", "-123", Ordering::Greater)]
    #[case("-123.1", "123", Ordering::Less)]
    #[case("123", "-123.1", Ordering::Greater)]
    #[case("-123", "123.0", Ordering::Less)]
    #[case("123", "-123.0", Ordering::Greater)]
    #[case("-123.0", "123", Ordering::Less)]
    #[case("123.0", "-123", Ordering::Greater)]
    #[case("-123", "123.00", Ordering::Less)]
    #[case("123.00", "-123", Ordering::Greater)]
    #[case("-123.00", "123", Ordering::Less)]
    #[case("123", "-123.00", Ordering::Greater)]
    #[case("-123", "123.01", Ordering::Less)]
    #[case("123.01", "-123", Ordering::Greater)]
    #[case("-123.01", "123", Ordering::Less)]
    #[case("123", "-123.01", Ordering::Greater)]
    // non-numeric
    #[case("123", "our", Ordering::Greater)]  // positive numbers considered greater than words
    #[case("own", "-123", Ordering::Greater)]  // negative numbers considered less than words
    #[case("our", "own", Ordering::Less)]  // negative numbers considered less than words
    #[case("own", "our", Ordering::Greater)]  // negative numbers considered less than words
    #[case("123our", "123own", Ordering::Less)]  // identical numeric prefix ignored
    #[case("123own", "123our", Ordering::Greater)]
    #[case("1234our", "123own", Ordering::Greater)]  // larger numeric prefix considered larger
    #[case("123own", "1234our", Ordering::Less)]
    #[case("12h34", "12h345", Ordering::Less)]  // non-decimal delimiter starts new integers
    #[case("12h345", "12h34", Ordering::Greater)]
    // multiple fields
    #[case("identical\t12.34", "identical\t12.340", Ordering::Less)]
    #[case("identical\t12.340", "identical\t12.34", Ordering::Greater)]
    #[case("identical\tlines\n", "identical\tlines\n", Ordering::Equal)]
    #[case("12\tfoo\n", "123\tfoo\n", Ordering::Less)]
    #[case("42\tfoo\n", "42\tbar\n", Ordering::Greater)]
    fn test_linecomp(#[case] l1: &str, #[case] l2: &str, #[case] expected: Ordering) {
        assert_eq!(
            tsv_cmp(l1, l2),
            expected,
            "tsv_cmp({}, {}) == {}, expected {}",
            l1,
            l2,
            tsv_cmp(l1, l2) as i8,
            expected as i8,
        );
    }
}
