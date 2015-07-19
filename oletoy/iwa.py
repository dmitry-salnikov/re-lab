# Copyright (C) 2013 David Tardon (dtardon@redhat.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 3 or later of the GNU General Public
# License as published by the Free Software Foundation.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
# USA
#

import struct

from utils import add_iter, add_pgiter, rdata

### General utils

def read(data, offset, fmt):
	return rdata(data, offset, fmt)[0]

def find_var(data, offset):
	"""Seek to the end of a variable-length number."""
	assert len(data) > offset
	off = offset
	c = ord(data[off])
	while off < len(data) and c & 0x80:
		off += 1
		c = ord(data[off])
	off += 1
	return off

def read_var(data, offset):
	"""Read a variable length number."""

	assert len(data) > offset

	cs = []
	off = offset
	c = ord(data[off])
	while off < len(data) and c & 0x80:
		cs.append(c & ~0x80)
		off += 1
		c = ord(data[off])
	cs.append(c)
	off += 1

	assert cs != []

	n = 0
	for c in reversed(cs):
		n = n << 7
		n += c

	return (n, off)

def get_or_default(dictionary, key, default):
	if dictionary.has_key(key):
		return dictionary[key]
	return default

### Compression

# The compression method (as I currently understand it)
#
# Compressed data are broken sequences of literals and references into
# previously uncompressed data. A reference consists of offset (taken
# backwards from the end of uncompressed data) and length. They are
# recongized by the first byte, as follows:
# + xxxxxx00 - a literal run
#   - In case this is not ffffxx00, this byte is followed by a single
#   byte containing count. This is in turn followed by count + 1
#   literals.
#   - If it is ffffnn00, nn is the number of bytes that contain the
#     count, minus 1. These bytes are in little endian order. Again,
#     this is followed by count + 1 literals.
# + hhhnnn01 - a "near" reference
#   - This is followed by another byte containing lower bits of offset
#     minus 1. The hhh bits of reference form higher bits of offset.
#     nnn bits are length - 4.
# + nnnnnn10 - a "far" reference
#   - This is followed by two bytes containing offset, in little endian
#     order. The nnnnnn bits of reference are length - 1.

def uncompress(data):
	result = bytearray()

	def append_ref(offset, length):
		assert offset <= len(result)
		if offset >= length:
			start = len(result) - offset
			result.extend(result[start:start + length])
		else:
			# The run of literals is inserted repeatedly
			i = len(result) - offset
			while length > 0:
				result.append(result[i])
				i += 1
				length -= 1

	off = 0
	(uncompressed_length, off) = read_var(data, off)

	while off < len(data):
		# print('at offset %x:' % (off + 4))
		c = ord(data[off])
		off += 1
		typ = c & 0x3

		if typ == 0: # literals
			if (c & 0xf0) == 0xf0:
				count = (c >> 2) & 0x3
				length = ord(data[off]) + 1
				off += 1
				i = 1
				while i <= count:
					b = ord(data[off])
					length += (b << i * 8)
					i += 1
					off += 1
			else:
				length = (c >> 2) + 1
			# print('  literal run: length = %x' % length)
			result.extend(data[off:off + length])
			off += length
		elif typ == 1: # near reference
			length = ((c >> 2) & 0x7) + 4
			high = c >> 5
			low = ord(data[off])
			offset = (high << 8) | low
			off += 1
			# print('  near ref: offset = %x, length = %x' % (offset, length))
			append_ref(offset, length)
		elif typ == 2: # far reference
			length = (c >> 2) + 1
			offset = ord(data[off]) | (ord(data[off + 1]) << 8)
			off += 2
			# print('  far ref: offset = %x, length = %x' % (offset, length))
			append_ref(offset, length)
		else:
			print("unknown type at offset 0x%x inside block" % (off + 4))
			assert False

	assert uncompressed_length == len(result)

	return result

### Protocol buffers parser

# Description of the wire format: https://developers.google.com/protocol-buffers/docs/encoding
# Note: this is rather simplified parser, tailored to the purpose of
# displaying the complete structure and values.

class result:
	def __init__(self, value, desc, start, end):
		self.value = value
		self.desc = desc
		self.start = start
		self.end = end

class varlen:
	def __init__(self, parser):
		self.size = None
		self.parser = parser

	def __call__(self, data, off):
		return self.parser(data, off)

class fixed:
	def __init__(self, size, fmt):
		self.size = size
		self.fmt = fmt

	def __call__(self, data, off):
		return rdata(data, off, self.fmt)[0]

class primitive:
	def __init__(self, parser, name):
		self.parser = parser
		self.name = name # A hack to get showing of packed arrays working
		self.primitive = True
		self.structured = False
		self.size = parser.size
		self.visualizer = None

	def __call__(self, data, off, start, end):
		return result(self.parser(data, off), self, start, end)

def parse_bool(data, off):
	return bool(read_var(data, off)[0])

def parse_int64(data, off):
	return read_var(data, off)[0]

def parse_sint64(data, off):
	return read_var(data, off)[0]

bool_ = primitive(varlen(parse_bool), 'bool')
int64 = primitive(varlen(parse_int64), 'int64')
sint64 = primitive(varlen(parse_sint64), 'sint64')
fixed32 = primitive(fixed(4, '<I'), 'fixed32')
sfixed32 = primitive(fixed(4, '<i'), 'sfixed32')
fixed64 = primitive(fixed(8, '<Q'), 'fixed64')
sfixed64 = primitive(fixed(8, '<q'), 'sfixed64')
float_ = primitive(fixed(4, '<f'), 'float')
double_ = primitive(fixed(8, '<d'), 'double')

class string:
	def __init__(self):
		self.primitive = False
		self.structured = False
		self.visualizer = 'iwa_string'

	def __call__(self, data, off, start, end):
		return result(data[off:end], self, start, end)

class packed:
	def __init__(self, item):
		self.item = item
		self.primitive = False
		self.structured = False
		if item.name:
			self.visualizer = 'iwa_packed_%s' % item.name
		else:
			self.visualizer = None

	def __call__(self, data, off, start, end):
		values = []
		extents = []
		while off < end:
			if self.item.size == None:
				orig = off
				off = find_var(data, off)
				values.append(self.item.parser(data, orig))
				extents.append((orig, off))
			else:
				values.append(self.item.parser(data, off))
				extents.append((off, off + self.item.size))
				off += self.item.size
		return self._result(values, extents, self, start, end)

	def _result(self, values, extents, desc, start, end):
		r = result(values, desc, start, end)
		r.extents = extents
		return r

class message:
	def __init__(self, desc=None):
		if desc:
			self.desc = desc
		else:
			self.desc = {}
		self.primitive = False
		self.structured = True
		self.visualizer = None

	def __call__(self, data, off, start, end):
		msg = {}
		while off < end:
			stt = off
			(key, off) = read_var(data, off)
			field_num = key >> 3
			wire_type = key & 0x7
			stt_data = off
			if wire_type == 0:
				off = find_var(data, off)
			elif wire_type == 1:
				off += 8
			elif wire_type == 2:
				(length, off) = read_var(data, off)
				stt_data = off
				off += length
			elif wire_type == 3 or wire_type == 4:
				pass
			elif wire_type == 5:
				off += 4
			else:
				raise self.unknown_type()
			if not msg.has_key(field_num):
				msg[field_num] = []
			desc = self._desc(field_num, wire_type)
			msg[field_num].append(desc(data, stt_data, stt, off))
		if off != end:
			raise self.bad_format()
		return result(msg, self, start, end)

	class unknown_type:
		pass

	class bad_format:
		pass

	def _desc(self, field, wire_type):
		class generic_desc:
			def __init__(self):
				self.primitive = False
				self.structured = False
				self.visualizer = None

			def __call__(self, data, off, start, end):
				if wire_type == 0:
					self.visualizer = 'iwa_varint'
				elif wire_type == 1:
					self.visualizer = 'iwa_64bit'
				elif wire_type == 2: # try to parse as a message
					try:
						desc = message()
						return desc(data, off, start, end)
					except:
						pass
				elif wire_type == 5:
					self.visualizer = 'iwa_32bit'
				return result(data[start:end], self, start, end)

		if self.desc.has_key(field):
			if self.desc[field][1]:
				return self.desc[field][1]
			elif self.desc[field][0]:
				global MESSAGES
				if MESSAGES[self.desc[field][0]]:
					return MESSAGES[self.desc[field][0]]
		return generic_desc()

### File parser

MESSAGES = {}

OBJ_NAMES = {}

OBJ_TYPES = {}

class IWAParser(object):

	def __init__(self, data, page, parent):
		self.data = data
		self.page = page
		self.parent = parent

	def parse(self):
		off = 0
		obj_num = 0
		while off < len(self.data):
			obj_start = off
			(hdr_len, off) = read_var(self.data, off)
			hdr = self._parse_header(off, hdr_len)
			data_len = 0
			obj_type = None
			if hdr.value.has_key(2):
				if hdr.value[2][0].value.has_key(1):
					obj_type = hdr.value[2][0].value[1][0].value
				if hdr.value[2][0].value.has_key(3):
					data_len = hdr.value[2][0].value[3][0].value
			obj_data = self.data[obj_start:off + hdr_len + data_len]
			if obj_type:
				if OBJ_NAMES.has_key(obj_type):
					obj_name = OBJ_NAMES[obj_type]
				else:
					obj_name = 'Object %d' % obj_type
			else:
				obj_name = 'Object'
			objiter = add_pgiter(self.page, '[%d] %s' % (obj_num, obj_name), 'iwa', 'iwa_object', obj_data, self.parent)
			self._add_pgiter('Header', hdr, off, off + hdr_len, objiter)
			off += hdr_len
			if data_len > 0:
				desc = message()
				if OBJ_TYPES.has_key(obj_type):
					desc = OBJ_TYPES[obj_type]
				data = self._parse_object(off, data_len, desc)
				self._add_pgiter('Data', data, off, off + data_len, objiter)
				off += data_len
			obj_num += 1

	_HEADER_MSG = message({2: ('Data info', message(
		{
			1: ('Object type?', int64),
			2: (None, packed(int64)),
			3: ('Data size', int64),
			5: ('Object IDs', packed(int64))
		}
	))})

	def _parse_header(self, off, length):
		return self._HEADER_MSG(self.data, off, off, off + length)

	def _parse_object(self, off, length, desc):
		return desc(self.data, off, off, off + length)

	def _add_pgiter(self, name, obj, start, end, parent):
		if obj.desc.primitive:
			name = '%s = %s' % (name, obj.value)
		if obj.desc.visualizer:
			visualizer = obj.desc.visualizer
		else:
			visualizer = 'iwa_field'
		it = add_pgiter(self.page, name, 'iwa', visualizer, self.data[start:end], parent)
		if obj.desc.structured:
			for (k, v) in obj.value.iteritems():
				single = len(v) == 1
				for (i, e) in zip(xrange(len(v)), iter(v)):
					if single:
						n = '%d' % k
					else:
						n = "%d[%d]" % (k, i)
					if obj.desc.desc.has_key(k):
						if obj.desc.desc[k][0]:
							n = '%s: %s' % (n, obj.desc.desc[k][0])
					self._add_pgiter(n, e, e.start, e.end, it)

### Data view callbacks

def add_iwa_compressed_block(hd, size, data):
	(length, off) = rdata(data, 1, '<H')
	add_iter(hd, 'Compressed length', length, off - 2, 2, '<H')
	off += 1
	var_off = off
	(ulength, off) = read_var(data, off)
	add_iter(hd, 'Uncompressed length', ulength, var_off, off - var_off, '%ds' % (off - var_off))

def add_iwa_object(hd, size, data):
	(length, off) = read_var(data, 0)
	add_iter(hd, 'Header length', length, 0, off, '%ds' % off)

def add_field(hd, size, data):
	(key, off) = read_var(data, 0)
	field_num = key >> 3
	wire_type = key & 0x7
	wire_type_map = {0: 'Varint', 1: '64-bit', 2: 'Length-delimited', 3: 'Start group', 4: 'End group', 5: '32-bit'}
	wire_type_str = get_or_default(wire_type_map, wire_type, 'Unknown')
	add_iter(hd, 'Field', field_num, 0, off, '%ds' % off)
	add_iter(hd, 'Wire type', wire_type_str, 0, off, '%ds' % off)
	if wire_type == 2:
		len_off = off
		(length, off) = read_var(data, off)
		add_iter(hd, 'Length', length, len_off, off - len_off, '%ds' % (off - len_off))
	return off

def add_32bit(hd, size, data):
	off = add_field(hd, size, data)
	f32 = read(data, off, '<I')
	s32 = read(data, off, '<i')
	f = read(data, off, '<f')
	add_iter(hd, 'Fixed32', f32, off, off + 4, '<I')
	add_iter(hd, 'Signed fixed32', s32, off, off + 4, '<i')
	add_iter(hd, 'Float', f, off, off + 4, '<f')

def add_64bit(hd, size, data):
	off = add_field(hd, size, data)
	f64 = read(data, off, '<Q')
	s64 = read(data, off, '<q')
	d = read(data, off, '<d')
	add_iter(hd, 'Fixed64', f64, off, off + 8, '<Q')
	add_iter(hd, 'Signed fixed64', s64, off, off + 8, '<q')
	add_iter(hd, 'Double', d, off, off + 8, '<d')

def add_packed(hd, size, data, parser, p16=False):
	off = add_field(hd, size, data)
	obj = parser(data, off, 0, size)
	i = 0
	for (v, e) in zip(obj.value, obj.extents):
		add_iter(hd, 'Value %d' % i, v, e[0], e[1] - e[0], '%ds' % (e[1] - e[0]))
		i += 1

def add_packed_bool(hd, size, data):
	add_packed(hd, size, data, packed(bool_))

def add_packed_int64(hd, size, data):
	add_packed(hd, size, data, packed(int64))

def add_packed_sint64(hd, size, data):
	add_packed(hd, size, data, packed(sint64))

def add_packed_fixed32(hd, size, data):
	add_packed(hd, size, data, packed(fixed32))

def add_packed_sfixed32(hd, size, data):
	add_packed(hd, size, data, packed(sfixed32))

def add_packed_fixed64(hd, size, data):
	add_packed(hd, size, data, packed(fixed64))

def add_packed_sfixed64(hd, size, data):
	add_packed(hd, size, data, packed(sfixed64))

def add_packed_float(hd, size, data):
	add_packed(hd, size, data, packed(float_))

def add_packed_double(hd, size, data):
	add_packed(hd, size, data, packed(double_))

def add_string(hd, size, data):
	off = add_field(hd, size, data)
	obj = string()(data, off, 0, size)
	add_iter(hd, 'String', obj.value, off, size - off, '%ds' % (size - off))

def add_varint(hd, size, data):
	off = add_field(hd, size, data)
	i = parse_int64(data, off)
	s = parse_sint64(data, off)
	b = parse_bool(data, off)
	add_iter(hd, 'Int', i, off, size - off, '%ds' % (size - off))
	add_iter(hd, 'Signed int', s, off, size - off, '%ds' % (size - off))
	add_iter(hd, 'Bool', b, off, size - off, '%ds' % (size - off))

iwa_ids = {
	'iwa_32bit': add_32bit,
	'iwa_64bit': add_64bit,
	'iwa_compressed_block': add_iwa_compressed_block,
	'iwa_field': add_field,
	'iwa_object': add_iwa_object,
	'iwa_packed_bool': add_packed_bool,
	'iwa_packed_int64': add_packed_int64,
	'iwa_packed_sint64': add_packed_sint64,
	'iwa_packed_fixed32': add_packed_fixed32,
	'iwa_packed_sfixed32': add_packed_sfixed32,
	'iwa_packed_fixed64': add_packed_fixed64,
	'iwa_packed_sfixed64': add_packed_sfixed64,
	'iwa_packed_float': add_packed_float,
	'iwa_packed_double': add_packed_double,
	'iwa_string': add_string,
	'iwa_varint': add_varint,
}

### Entry point

def open(data, page, parent):
	n = 0
	off = 0
	uncompressed_data = bytearray()

	while off < len(data):
		off += 1
		(length, off) = rdata(data, off, '<H')
		off += 1

		block = data[off - 4:off + int(length)]
		blockiter = add_pgiter(page, 'Block %d' % n, 'iwa', 'iwa_compressed_block', block, parent)
		uncompressed = uncompress(block[4:])
		uncompressed_data.extend(uncompressed)
		add_pgiter(page, 'Uncompressed', 'iwa', 0, str(uncompressed), blockiter)

		n += 1
		off += length

	uncompressed_data = str(uncompressed_data)
	dataiter = add_pgiter(page, 'Uncompressed', 'iwa', 0, uncompressed_data, parent)
	parser = IWAParser(uncompressed_data, page, dataiter)
	parser.parse()

# vim: set ft=python sts=4 sw=4 noet:
