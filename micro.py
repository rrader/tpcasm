from functools import partial, reduce
from tools import *

JUMPS = ['mjmp', 'mjc', 'mjz', 'mjs']
NOOPS = ['mjcmd', 'mnop', 'end']
ONEOPT = JUMPS
DELAY = {
    'mmov': 3, 'mmovl': 3, 'mjmp': 3, 'mjz': 3, 'mjc': 3, 'madd': 3,
    'msub': 3, 'mor': 3, 'mxor': 3, 'mand': 3, 'mshl': 3, 'mshr': 3,
    'mjcmd': 3, 'mnop': 3, 'min': 3, 'mout': 3,
}

CMD = {
    'label': -1, 'mmov': 0, 'mmovl': 1, 'mjmp': 2,  # (mjc) по кол-ву флагов
    'mjz': 2, 'mjc': 2, 'madd': 3, 'msub': 4, 'mor': 5, 'mxor': 6, 'mand': 7,
    'mshl': 8, 'mshr': 9, 'mjcmd': 10, 'mnop': 11,
}

OP = {
    'FFFF': 18, 'op1r': 24, '0': 17, '1': 16, 'op1w': 25, 'MEM': 19,
    'R11': 15, 'EXT': 20, 'CMD': 3, 'NUL': 0, 'SP': 1, 'op2r': 26,
    '@SP': 21, '@IC': 22, 'FLAGS': 2, 'IC': 31, 'PORT': 30, 'IENC': 23,
    'R5': 9, 'R4': 8, 'R7': 11, 'R6': 10, 'R1': 5, 'R0': 4, 'R3': 7,
    'R2': 6, 'R9': 13, 'R8': 12, 'R10': 14, 'PORT[R0]': 29}


#parse

LEN = 6
is_offset_cmd = lambda _: _[0] == "#offset"
get_offset = lambda _: int(_[1], 0)
offset = lambda cmd, start_addr: get_offset(cmd) - 1 if is_offset_cmd(cmd) \
    else start_addr + 1

offset_dict = lambda item, start_addr: \
    (lambda _: {'cmd': _, 'offset': offset(_, start_addr)})(item)

bulk_dict = lambda cmds, labels: {'cmds': cmds, 'labels': labels}


def append_cmd(bulk, _):
    bulk['cmds'].append(_)
    if _['cmd'][0] == "label":
        bulk['labels'][_['cmd'][1]] = _['offset']
    return bulk

new_offset = lambda processed, new: \
    append_cmd(processed, offset_dict(new, tail(processed['cmds'])['offset']))

is_instruction = lambda _: not is_offset_cmd(_['cmd'])

drop_first_cmd = lambda _: {'cmds': _['cmds'][1:],
                            'labels': _['labels']}

calc_offsets = lambda iterable: \
    drop_first_cmd(reduce(new_offset, iterable,
                   bulk_dict([{'cmd': None, 'offset': -1}], {})))

filter_instructions = lambda bulk: \
    bulk_dict(
        list(filter(is_instruction, bulk['cmds'])),
        bulk['labels'])

subs_label = lambda _: ('mnop', '', '', [])
label_nop = lambda _: \
    {'cmd': subs_label(_), 'offset': _['offset']} \
    if _['cmd'][0] == "label" else _

subs_jmp = lambda _, labels: (_[0], "J%s:%d" % (_[0], labels[_[1]]),
                              _[2], _[3])


def link_cmd(labels):
    return lambda _: \
        {'cmd': subs_jmp(_['cmd'], labels), 'offset': _['offset']} \
        if _['cmd'][0] in JUMPS else _

link = lambda bulk: map(link_cmd(bulk['labels']), bulk['cmds'])

#translate


def parseop(op):
    ext = None
    try:
        op1 = OP[op]
    except KeyError:
        if op[0] == 'P':
            op1 = OP['PORT']
            ext = int(op[1:], 0)
        if op[0] == "#":
            op1 = OP['EXT']
            ext = int(op[1:], 0)
        if op[0] == "J":
            op1 = JUMPS.index(op[1:].split(':')[0])
            ext = int(op[1:].split(':')[1], 0)
        if op[0] == "@":
            op1 = OP['MEM']
            ext = int(op[1:], 0)
    return op1, ext


b2cmd = lambda _: bin_str(CMD[_['cmd'][0]], 4)
b2op1d = lambda _: parseop(_['cmd'][1]) if _['cmd'][0] not in NOOPS \
    else (0, None)
b2op2d = lambda _: parseop(_['cmd'][2]) if _['cmd'][0] not in ONEOPT+NOOPS \
    else (0, None)

b2ext = lambda b2ext1, b2ext2: b2ext1 if b2ext1 else b2ext2 if b2ext2 else 0


def b2data(_):
    b2op1, b2op1ext = b2op1d(_)
    b2op2, b2op2ext = b2op2d(_)
    return "%s%s%s" % (bin_str(b2ext(b2op1ext, b2op2ext), 16),
                       bin_str(b2op2, 5),
                       bin_str(b2op1, 5))

allow_flags = lambda _: "1" if "flags" in _['cmd'][3] else "0"

beta1 = lambda _: '1' if _['cmd'][0] in JUMPS else '0'
beta2 = lambda _: '0%s%s%s' % (allow_flags(_), b2data(_), b2cmd(_))
beta3 = lambda _: bin_str(DELAY[_['cmd'][0]], 8)
beta4 = lambda _: str(int('0b%s%s%s' % (beta1(_), beta2(_), beta3(_)), 2) % 2)

translate_command = lambda _: \
    (int("0b%s%s%s%s%s" % ("1"*6, beta4(_), beta3(_),
                           beta2(_), beta1(_), ), 2), _['offset']) \
    if _['cmd'][0] != 'end' else (-1, _['offset'])
translate_commands = partial(map, translate_command)
nop_labels = partial(map, label_nop)

#to Intel HEX


def end_statement(_):
    addr = hex_str(_[1] * LEN, 4)
    load = "%s01" % addr
    return ":00%s%s" % (load, checksum(load))


load = lambda _: hex_str(LEN, 2) + \
    hex_str(_[1] * LEN, 4) + '00' + \
    hex_str(_[0], 12)

cs = lambda _: checksum(load(_))

intel_hex = partial(map,
                    lambda _: ":%s%s" % (load(_), cs(_)) if _[0] != -1 else
                    end_statement(_))


def process(iterable):
    preprocessed = \
        preprocess_labels(iterable)

    offsetted = \
        filter_instructions(calc_offsets(parse_instructions(preprocessed)))

    linked = \
        link(offsetted)
    return intel_hex(translate_commands(nop_labels(linked)))
