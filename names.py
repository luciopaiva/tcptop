
with open('names.txt') as file:
    names = [line.strip() for line in file]

def string_to_name(s):
    i = hash(s)
    return names[i % len(names)]
