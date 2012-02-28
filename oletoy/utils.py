# Copyright (C) 2007,2010,2011	Valek Filippov (frob@df.ru)
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

import sys,struct

def add_iter (hd,name,value,offset,length,vtype,offset2=0,length2=0,parent=None):
	iter = hd.hdmodel.append(parent, None)
	hd.hdmodel.set (iter, 0, name, 1, value,2,offset,3,length,4,vtype,5,offset2,6,length2)
	return iter

def add_pgiter (page, name, ftype, stype, data, parent = None):
	iter1 = page.model.append (parent,None)
	page.model.set_value(iter1,0,name)
	page.model.set_value(iter1,1,(ftype,stype))
	if data != None:
		page.model.set_value(iter1,2,len(data))
		page.model.set_value(iter1,3,data)
	page.model.set_value(iter1,6,page.model.get_string_from_iter(iter1))
	return iter1


def hex2d(data):
	res = ''
	data = data.replace(" ","")
	for i in range(len(data)/2):
		num = int(data[i*2:i*2+2],16)
		res += struct.pack("B",num)
	return res

def d2hex(data,space=""):
	s = ""
	for i in range(len(data)):
		s += "%02x%s"%(ord(data[i]),space)
	return s