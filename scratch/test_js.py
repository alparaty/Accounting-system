with open('js/onyx_app.js', encoding='utf-8') as f:
    content = f.read()

braces = 0
parens = 0
brackets = 0
for idx, char in enumerate(content):
    if char == '{': braces += 1
    elif char == '}': braces -= 1
    elif char == '(': parens += 1
    elif char == ')': parens -= 1
    elif char == '[': brackets += 1
    elif char == ']': brackets -= 1

print(f"Braces balance: {braces}, Parens balance: {parens}, Brackets balance: {brackets}")
if braces == 0 and parens == 0 and brackets == 0:
    print("ALL BALANCED PERFECTLY!")
else:
    print("WARNING: IMBALANCE DETECTED!")
