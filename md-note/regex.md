# regex Module(Regular Expression)

## methods
### `.finditer()` and `.findall()`
```py
import re

pattern = re.compile(r"abc")
matches = pattern.finditer("123abcHASDJFabcLANa3f")

for match in matches:
    print(match)
# there are also several functions for the finditer object: span, group, start, end
    print(match.span(), match.group(), "end:", match.end(), "start:",match.start())
# <re.Match object; span=(3, 6), match='abc'>
# (3, 6) abc end: 6 start: 3
# <re.Match object; span=(12, 15), match='abc'>
# (12, 15) abc end: 15 start: 12

```

## meta chars
- `.` Any character (except newline character)
- `^` Starts with "^hello"
- `$` Ends with "world$"
- `*` Zero or more occurrences "aix*"
- `+` One or more occurrences "aix+"
- `{ }` Exactly the specified number of occurrences "al{2}"
- `[]` A set of characters "[a-m]"
- `\` Special sequence (or escape special characters) `"\\d"` = "\\d"
- `|` Either or "falls|stays"
- `( )` Capture and group

## Special Sequence
- `\d` : Matches any decimal digit; [0-9].
- `\D` : Matches any non-digit character;
- `\s` : Matches any whitespace character; (space " " tab "\t" newline "\n")
- `\S` : Matches any non-whitespace character;
- `\w` : Matches any alphanumeric (word) character; [a-zA-Z0-9_].
- `\W` : Matches any non-alphanumeric character;
- `\b` : Matches where the specified characters are at the beginning or at the end of a word r"\bain" r"ain\b"
- `\B` : Matches where the specified characters are present, but NOT at the beginning (or at the end) of a word r"\Bain" r"ain\B"

## Sets
`[]` = for a specific pattern
```py
import re

# 3 lowercase letters
# 3-5 digits
# one symbol
# up to two uppercase characters (optional)

pattern = re.compile(r"^[a-z]{3}[0-9]{3,5}[^a-zA-Z0-9]{1}[A-Z]{0,2}$")
print(pattern.search("ahd2331#AJ"))
print(pattern.search("lll44511.K"))
print(pattern.search("lll44511."))
print(pattern.search("abc123456#JJ"))
```

## Quantifier
- `*`: 0 or more
- `+`: 1 or more
- `?`: 0 or 1, -> optional character
- `{4}`: exact number
- `{4,6}`: range numbers (min, max) 

## Modification
### split
```py
import re

test_string = '123abc456789abc123ABC'
pattern = re.compile(r"abc")
splitted = pattern.split(test_string)
print(splitted)

#output: ['123', '456789', '123ABC']
```

### sub
```py
import re

# split, sub

test_string = 'hello world, you are the best world'
pattern = re.compile(r"world")
subbed_string = pattern.sub("planet", test_string)
print(subbed_string)

#output: hello planet, you are the best planet
```

### escape
```py
import re

user_input = "Google.com"

# Without re.escape(), the dot is a wildcard
print(re.findall(user_input, "Google1com"))  # Output: ['Google1com']

# With re.escape()
safe_input = re.escape(user_input)
print(safe_input)                             # Output: Google\.com
print(re.findall(safe_input, "Google1com"))  # Output: [] (No match, as expected)
```