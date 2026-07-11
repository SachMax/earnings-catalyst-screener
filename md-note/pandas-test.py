import re

pattern = re.compile(r"abc")
matches = list(pattern.finditer("123abcHASDJFabcLANa3f"))
print(len(matches))
for match in matches:
    print(match)