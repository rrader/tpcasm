import re
from functools import partial
from itertools import zip_longest

strip = partial(map, lambda _: _.strip())
strip_empty = partial(filter, lambda _: _.strip())
remove_comments = partial(map, lambda _: _.split(';')[0].strip())

bin_str = lambda _, digits: bin(_)[2:].zfill(digits)
hex_str = lambda _, digits: hex(_)[2:].zfill(digits)


def grouper(n, iterable, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def checksum(data):
    cs = 0
    for m in grouper(2, data):
        cs += int(''.join(m), 16)

    r = int(hex(cs)[2:][-2:], 16)
    r = (0x100 - r) & 0xFF  # two's complement
    return hex(r)[2:][-2:].zfill(2)

tail = lambda _: _[-1]

labels = lambda _: re.findall("\s*(.*):\s*", _)
label = lambda _: labels(_)[0]
is_label = lambda _: bool(labels(_))

preprocess_labels = partial(map, lambda _:
                            "label " + label(_) if is_label(_) else _)

command = lambda _: _.split()[0]
noncommand = lambda _: ' '.join(_.split()[1:])
args = lambda _: noncommand(_).split(',')
args_count = lambda _: len(args(_))
op = lambda _, n: args(_)[n-1].strip() if args_count(_) >= n else ""

additional = lambda _: list(strip(strip_empty(args(_)[2:])))
parse_instruction = lambda _: (command(_), op(_, 1), op(_, 2), additional(_))
parse_instructions = partial(map, parse_instruction)
