fn linecomp(l1: &str, l2: &str) -> i32 {
    let mut p1 = 0;
    let mut p2 = 0;
    let mut prev_p1 = 999999;
    let mut prev_p2 = 999999;

    'next_field: loop {
        if p1 == prev_p1 && p2 == prev_p2 {
            panic!("Infinite loop in linecomp");
        }
        prev_p1 = p1;
        prev_p2 = p2;

        if p1 >= l1.len() {
            return if p2 >= l2.len() { 0 } else { -1 };
        }
        if p2 >= l2.len() {
            return 1;
        }

        let mut l1_larger = 1;
        if l1.chars().nth(p1).unwrap() == '-' {
            if l2.chars().nth(p2).unwrap() != '-' {
                // l1 is negative, l2 is positive, so l1 < l2
                return -1;
            }
            // both are negative, skip the minus sign, remember to reverse the result
            p1 += 1;
            p2 += 1;
            l1_larger = -1;
        } else if l2.chars().nth(p2).unwrap() == '-' {
            // l2 is negative, l1 is positive, so l1 > l2
            return 1;
        }

        // skip leading zeros in l1
        while p1 < l1.len() && l1.chars().nth(p1).unwrap() == '0' {
            p1 += 1;
        }

        // skip leading zeros in l2
        while p2 < l2.len() && l2.chars().nth(p2).unwrap() == '0' {
            p2 += 1;
        }

        let mut d1 = p1;
        while d1 < l1.len() && l1.chars().nth(d1).unwrap().is_ascii_digit() {
            d1 += 1;
        }

        let mut d2 = p2;
        while d2 < l2.len() && l2.chars().nth(d2).unwrap().is_ascii_digit() {
            d2 += 1;
        }

        if d1 - p1 > d2 - p2 {
            // l1 has more integer digits than l2, so |l1| > |l2|
            return l1_larger;
        }
        if d1 - p1 < d2 - p2 {
            // l1 has fewer integer digits than l2, so |l1| < |l2|
            return -l1_larger;
        }

        if &l1[p1..d1] > &l2[p2..d2] {
            // l1 has the same number of integer digits as l2, but |l1| > |l2|
            return l1_larger;
        }
        if &l1[p1..d1] < &l2[p2..d2] {
            // l1 has the same number of integer digits as l2, but |l1| < |l2|
            return -l1_larger;
        }

        if d1 >= l1.len() {
            return if d2 >= l2.len() { 0 } else { -l1_larger };
        }
        if d2 >= l2.len() {
            return l1_larger;
        }

        if l1.chars().nth(d1).unwrap() > l2.chars().nth(d2).unwrap() {
            // a different non-digit character follows identical digits in l1 and l2
            // and it sorts l1 after l2
            return l1_larger;
        }
        if l1.chars().nth(d1).unwrap() < l2.chars().nth(d2).unwrap() {
            // a different non-digit character follows identical digits in l1 and l2
            // and it sorts l1 before l2
            return -l1_larger;
        }

        if l1.chars().nth(d1).unwrap() != '.' {
            // the non-digit characters are not a decimal point, continue comparison
            // after it
            p1 = d1 + 1;
            p2 = d2 + 1;
            continue;
        }
        // l1 and l2 have the same integer part, compare the fractional part
        p1 = d1 + 1;
        p2 = d2 + 1;
        loop {
            if p1 >= l1.len() {
                return if p2 >= l2.len() { 0 } else { -l1_larger };
            }
            if p2 >= l2.len() {
                return l1_larger;
            }
            if l1.chars().nth(p1).unwrap() == '\t' {
                if l2.chars().nth(p2).unwrap() == '\t' {
                    // l1 and l2 have the same fractional part, they are equal
                    p1 += 1;
                    p2 += 1;
                    continue 'next_field;
                }
                // l1 has fewer fractional digits than l2, so |l1| < |l2|
                return -l1_larger;
            }
            if l2.chars().nth(p2).unwrap() == '\t' {
                // l1 has more fractional digits than l2, so |l1| > |l2|
                return l1_larger;
            }
            if l1.chars().nth(p1).unwrap() > l2.chars().nth(p2).unwrap() {
                // fractional part of l1 is greater than that of l2, so |l1| > |l2|
                return l1_larger;
            }
            if l1.chars().nth(p1).unwrap() < l2.chars().nth(p2).unwrap() {
                // fractional part of l1 is less than that of l2, so |l1| < |l2|
                return -l1_larger;
            }
            // l1 and l2 have the same fractional part up to here, continue comparison
            p1 += 1;
            p2 += 1;
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
    // integers
    #[case("123", "123", 0)]
    #[case("123", "124", -1)]
    #[case("124", "123", 1)]
    #[case("123", "1234", -1)]
    #[case("1234", "123", 1)]
    #[case("-123", "123", -1)]
    #[case("123", "-123", 1)]
    #[case("-123", "-123", 0)]
    #[case("-123", "-124", 1)]
    #[case("-124", "-123", -1)]
    // integers vs. floats
    #[case("123", "123.0", -1)] // by convention, shorter notation is less than longer
    #[case("123", "123.1", -1)]
    #[case("123.1", "123", 1)]
    #[case("123.0", "123", 1)] // by convention, shorter notation is less than longer
    #[case("123.0", "123.1", -1)]
    #[case("123.1", "123.0", 1)]
    #[case("123.0", "123.01", -1)]
    #[case("123.01", "123.0", 1)]
    // floats
    #[case("123.0", "123.0", 0)]
    #[case("123.0", "123.1", -1)]
    #[case("123.1", "123.0", 1)]
    #[case("123.0", "123.00", -1)]  // by convention, shorter notation less than longer
    #[case("123.00", "123.0", 1)]  // by convention, shorter notation less than longer-
    #[case("123.0", "123.01", -1)]
    #[case("123.01", "123.0", 1)]
    #[case("123.0", "124.0", -1)]
    #[case("124.0", "123.0", 1)]
    #[case("123.0", "124.1", -1)]
    #[case("124.1", "123.0", 1)]
    #[case("123.0", "124.00", -1)]
    #[case("124.00", "123.0", 1)]
    #[case("123.0", "124.01", -1)]
    #[case("124.01", "123.0", 1)]
    // negative floats
    #[case("-123.0", "123.0", -1)]
    #[case("123.0", "-123.0", 1)]
    #[case("-123.0", "-123.0", 0)]
    #[case("-123.0", "-123.1", 1)]
    #[case("-123.1", "-123.0", -1)]
    #[case("-123.0", "-123.00", 1)]  // by convention, shorter notation less than long
    #[case("-123.00", "-123.0", -1)]  // by convention, shorter notation less than long
    #[case("-123.02", "-123.01", -1)]
    #[case("-123.01", "-123.02", 1)]
    #[case("-123.00", "-123.01", 1)]
    #[case("-123.01", "-123.00", -1)]
    #[case("-123.0", "-123.01", 1)]
    #[case("-123.01", "-123.0", -1)]
    #[case("-123.0", "-124.0", 1)]
    #[case("-124.0", "-123.0", -1)]
    #[case("-123.0", "-124.1", 1)]
    #[case("-124.1", "-123.0", -1)]
    #[case("-123.0", "-124.00", 1)]
    #[case("-124.00", "-123.0", -1)]
    #[case("-123.0", "-124.01", 1)]
    #[case("-124.01", "-123.0", -1)]
    // negative integers
    #[case("-123", "123", -1)]
    #[case("123", "-123", 1)]
    #[case("-123", "-123", 0)]
    #[case("-123", "-124", 1)]
    #[case("-124", "-123", -1)]
    // negative integers vs. floats
    #[case("-123", "123.0", -1)]
    #[case("123", "-123.0", 1)]
    #[case("-123.0", "123", -1)]
    #[case("123.0", "-123", 1)]
    #[case("-123", "123.1", -1)]
    #[case("123.1", "-123", 1)]
    #[case("-123.1", "123", -1)]
    #[case("123", "-123.1", 1)]
    #[case("-123", "123.0", -1)]
    #[case("123", "-123.0", 1)]
    #[case("-123.0", "123", -1)]
    #[case("123.0", "-123", 1)]
    #[case("-123", "123.00", -1)]
    #[case("123.00", "-123", 1)]
    #[case("-123.00", "123", -1)]
    #[case("123", "-123.00", 1)]
    #[case("-123", "123.01", -1)]
    #[case("123.01", "-123", 1)]
    #[case("-123.01", "123", -1)]
    #[case("123", "-123.01", 1)]

    fn test_linecomp(#[case] l1: &str, #[case] l2: &str, #[case] expected: i32) {
        assert_eq!(
            linecomp(l1, l2),
            expected,
            "linecomp({}, {}) == {}, expected {}",
            l1,
            l2,
            linecomp(l1, l2),
            expected
        );
    }
}
