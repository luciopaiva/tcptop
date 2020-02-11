
with open('names.txt') as f:
    names = [line.strip() for line in f]


def string_to_name(s):
    i = hash(s)
    return names[i % len(names)]
