use pyo3::prelude::*;
use external_sort::{ExternalSorter, ExternallySortable};
use std::cmp::Ordering::{self, Equal, Greater, Less};
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Read, Seek, SeekFrom, Write};
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
        Less => -1,
        Equal => 0,
        Greater => 1,
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

macro_rules! DIGIT {
    () => {
        Some('0'..='9')
    };
}



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
    let mut input_file = File::open(input)?;
    input_file.seek(SeekFrom::Start(start))?;
    // Wrap the input file in a buffered reader
    let mut input = BufReader::new(&mut input_file);
    // Create an iterator which reads lines until the end marker and doesn't consume the end marker
    // See https://stackoverflow.com/questions/39935158 for `.by_ref()` explanation
    let binding = input.by_ref().lines().peekable();
    let lines = binding
        .take_while(|line| line.as_ref().map(|l| l != SQL_COPY_END).unwrap_or(false))
        .map(|line| TsvLine::new(&line.unwrap()));
    // Do the external sort
    let iter = ExternalSorter::new(1000000, None).sort_by(
        lines,
        |a, b| tsv_cmp(a.the_line.as_str(), b.the_line.as_str()),
    ).unwrap();
    // Append the sorted lines to the output file
    let output_file = OpenOptions::new().append(true).open(output)?;
    let mut output = BufWriter::new(output_file);
    for line in iter {
        writeln!(output, "{}", line.unwrap().the_line)?;
    }
    // Write the end marker (which was not consumed by peeking_take_while)
    writeln!(output, "{SQL_COPY_END}")?;
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
/// assert_eq!(tsv_cmp("123", "123"), Equal);
/// assert_eq!(tsv_cmp("123", "124"), Less);
/// assert_eq!(tsv_cmp("124", "123"), Greater);
/// assert_eq!(tsv_cmp("123\tour", "123\town"), Less);
///
pub fn tsv_cmp(l1: &str, l2: &str) -> Ordering {
    let mut l1_chars = l1.chars().peekable();
    let mut l2_chars = l2.chars().peekable();
    let mut l1_larger;

    'next_field: loop {
        // handle negative prefixes and end of lines
        l1_larger = Greater;  // reset negative prefix status for each new field
        match (l1_chars.peek(), l2_chars.peek()) {
            (Some('-'), Some('-')) => {  // both l1 and l2 have negative prefixes
                l1_larger = Less;  // invert the comparison of absolute values
                // skip the negative prefixes and start comparing absolute values
                l1_chars.next();
                l2_chars.next();
            }
            (Some('-'), Some(_)) => {  // only l1 has a negative prefix, so l1 < l2
                return Less;
            }
            (Some(_), Some('-')) => {  // only l2 has a negative prefix, so l1 > l2
                return Greater;
            }
            (Some(_), Some(_)) => {}  // neither has a negative prefix, continue
            (Some(_), None) => return Greater,  // end of line for l2, so l1 > l2
            (None, Some(_)) => return Less,  // end of line for l1, so l1 < l2
            (None, None) => return Equal,  // end of both lines, so l1 == l2
        }

        skip_leading_zeros(&mut l1_chars);
        skip_leading_zeros(&mut l2_chars);

        let mut sorting_so_far = Equal;
        loop {
            match (l1_chars.next(), l2_chars.next(), sorting_so_far) {
                // digits so far were identical, compare next digit. DIGIT!() matches '0'..='9'
                (c1 @ DIGIT!(), c2 @ DIGIT!(), Equal) => sorting_so_far = c1.cmp(&c2),

                // integer part ends in l1 or l2 before the other
                (_, DIGIT!(), Equal) => return l1_larger.reverse(),  // l1 integer part shorter
                (DIGIT!(), _, Equal) => return l1_larger,  // l1 integer part longer

                // integer parts unequal and both end here (EOL, end of field, or decimal point)
                (None | Some('\t' | '.'), None | Some('\t' | '.'), Less) => return l1_larger.reverse(),
                (None | Some('\t' | '.'), None | Some('\t' | '.'), Greater) => return l1_larger,

                // integer parts equal and both end here (EOL, end of field, or decimal point)
                (None, None, Equal) => return Equal,  // end of line for both, so l1 == l2
                (Some('\t'), Some('\t'), Equal) => continue 'next_field,  // end of field, continue
                (Some('.'), Some('.'), Equal) => break,  // same int parts, now compare fractions
                (Some('.'), Some(_), Equal) => return l1_larger,  // l1 decimal, l2 int, |l1| > |l2|
                (Some(_), Some('.'), Equal) => return l1_larger.reverse(),  // l2 decimal, l1 int

                // l1 is longer than l2
                (Some(_), None | Some('\t'), _) => return l1_larger,
                // l1 is shorter than l2
                (None | Some('\t'), Some(_), _) => return l1_larger.reverse(),

                // non-digits after equal integer parts, sort lexicographically
                (c1 @ Some(_), c2 @ Some(_), Equal) => sorting_so_far = c1.cmp(&c2),
                (Some(_), Some(_), Less) => return l1_larger.reverse(),
                (Some(_), Some(_), Greater) => return l1_larger,
            }
        }

        // l1 and l2 have the same integer part, compare the fractional part
        loop {
            match (l1_chars.next(), l2_chars.next()) {
                (Some('\t'), Some('\t')) => continue 'next_field,  // values equal, continue
                (Some(_), None | Some('\t')) => return l1_larger,  // l1 longer, so |l1| > |l2|
                (None | Some('\t'), Some(_)) => return l1_larger.reverse(),  // l2 long, |l1| < |l2|
                (None, None) => return Equal,  // end of both lines, so l1 == l2
                (Some(c1), Some(c2)) => {  // compare characters and return as soon as they differ
                    match c1.cmp(&c2) {
                        Less => return l1_larger.reverse(),
                        Greater => return l1_larger,
                        Equal => continue,
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
    #[case("123", "123", Equal)]
    #[case("123", "124", Less)]
    #[case("124", "123", Greater)]
    // integers, different length
    #[case("123", "1234", Less)]
    #[case("1234", "123", Greater)]
    // negative integers
    #[case("-123", "123", Less)]
    #[case("123", "-123", Greater)]
    #[case("-123", "-123", Equal)]
    #[case("-123", "-124", Greater)]
    #[case("-124", "-123", Less)]
    // integers vs. floats
    #[case("123", "122.9", Greater)]
    #[case("123", "123.0", Less)] // by convention, shorter notation is less than longer
    #[case("123", "123.1", Less)]
    #[case("123.1", "123", Greater)]
    #[case("123.0", "123", Greater)] // by convention, shorter notation is less than longer
    #[case("122.9", "123", Less)]
    // floats vs. floats, equal length, same integer part
    #[case("123.1", "123.1", Equal)]
    #[case("123.0", "123.1", Less)]
    #[case("123.1", "123.0", Greater)]
    // floats vs. floats, different length, same integer part
    #[case("123.0", "123.01", Less)]
    #[case("123.01", "123.0", Greater)]
    #[case("123.0", "123.00", Less)] // by convention, shorter notation less than longer
    #[case("123.00", "123.0", Greater)] // by convention, shorter notation less than longer-
    // floats vs. floats, same length, different integer part
    #[case("123.0", "124.0", Less)]
    #[case("124.0", "123.0", Greater)]
    #[case("123.0", "124.1", Less)]
    #[case("124.1", "123.0", Greater)]
    // floats vs. floats, different length, different integer part
    #[case("123.0", "124.00", Less)]
    #[case("124.00", "123.0", Greater)]
    #[case("123.0", "124.01", Less)]
    #[case("124.01", "123.0", Greater)]
    // negative floats
    #[case("-123.0", "123.0", Less)]
    #[case("123.0", "-123.0", Greater)]
    #[case("-123.0", "-123.0", Equal)]
    #[case("-123.0", "-123.1", Greater)]
    #[case("-123.1", "-123.0", Less)]
    #[case("-123.0", "-123.00", Greater)] // by convention, shorter notation less than long
    #[case("-123.00", "-123.0", Less)] // by convention, shorter notation less than long
    #[case("-123.02", "-123.01", Less)]
    #[case("-123.01", "-123.02", Greater)]
    #[case("-123.00", "-123.01", Greater)]
    #[case("-123.01", "-123.00", Less)]
    #[case("-123.0", "-123.01", Greater)]
    #[case("-123.01", "-123.0", Less)]
    #[case("-123.0", "-124.0", Greater)]
    #[case("-124.0", "-123.0", Less)]
    #[case("-123.0", "-124.1", Greater)]
    #[case("-124.1", "-123.0", Less)]
    #[case("-123.0", "-124.00", Greater)]
    #[case("-124.00", "-123.0", Less)]
    #[case("-123.0", "-124.01", Greater)]
    #[case("-124.01", "-123.0", Less)]
    // negative integers vs. floats
    #[case("-123", "123.0", Less)]
    #[case("123", "-123.0", Greater)]
    #[case("-123.0", "123", Less)]
    #[case("123.0", "-123", Greater)]
    #[case("-123", "123.1", Less)]
    #[case("123.1", "-123", Greater)]
    #[case("-123.1", "123", Less)]
    #[case("123", "-123.1", Greater)]
    #[case("-123", "123.0", Less)]
    #[case("123", "-123.0", Greater)]
    #[case("-123.0", "123", Less)]
    #[case("123.0", "-123", Greater)]
    #[case("-123", "123.00", Less)]
    #[case("123.00", "-123", Greater)]
    #[case("-123.00", "123", Less)]
    #[case("123", "-123.00", Greater)]
    #[case("-123", "123.01", Less)]
    #[case("123.01", "-123", Greater)]
    #[case("-123.01", "123", Less)]
    #[case("123", "-123.01", Greater)]
    // non-numeric
    #[case("123", "our", Greater)]  // positive numbers considered greater than words
    #[case("own", "-123", Greater)]  // negative numbers considered less than words
    #[case("our", "own", Less)]  // negative numbers considered less than words
    #[case("own", "our", Greater)]  // negative numbers considered less than words
    #[case("123our", "123own", Less)]  // identical numeric prefix ignored
    #[case("123own", "123our", Greater)]
    #[case("1234our", "123own", Greater)]  // larger numeric prefix considered larger
    #[case("123own", "1234our", Less)]
    #[case("12h34", "12h345", Less)]  // non-decimal delimiter starts new integers
    #[case("12h345", "12h34", Greater)]
    // multiple fields
    #[case("identical\t12.34", "identical\t12.340", Less)]
    #[case("identical\t12.340", "identical\t12.34", Greater)]
    #[case("identical\tlines\n", "identical\tlines\n", Equal)]
    #[case("12\tfoo\n", "123\tfoo\n", Less)]
    #[case("42\tfoo\n", "42\tbar\n", Greater)]
    #[case("-42\tbar\n", "-42\tfoo\n", Less)]
    #[case("-42\tfoo\n", "-42\tbar\n", Greater)]
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
