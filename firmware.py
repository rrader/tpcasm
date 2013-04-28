from functools import partial, reduce
from tools import *

JUMPS = ['jmp', 'jc', 'jz', 'js']
NOOPS = ['nop', 'end']
ONEOPT = JUMPS

CMD = {
    'label': -1, 'mov': 0, 'jmp': 2,
    'jz': 2, 'jc': 2, 'add': 3, 'sub': 4, 'or': 5, 'xor': 6, 'and': 7,
    'shl': 8, 'shr': 9, 'nop': 11,
    'out': 12, 'in': 13,
}

OP = {
    'NUL': 0, 'G0': 1, 'EXT': 2}


#parse

LEN = 4
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

cmd = lambda _: bin_str(CMD[_['cmd'][0]], 6)
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

beta2 = lambda _: '0%s%s' % (b2cmd(_), b2data(_))

translate_command = lambda _: \
    (int("0b%s" % (beta2(_), ), 2), _['offset']) \
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
