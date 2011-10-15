# Copyright (C) 2007-2011,	Valek Filippov (frob@df.ru)
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

import sys,struct,tree,zlib,fhparse,gtk,gobject

chunks = { "BrushTip":fhparse.BrushTip, "Brush":fhparse.Brush, "VDict":fhparse.VDict, "UString":fhparse.UString, "SymbolClass":fhparse.SymbolClass,\
				"PerspectiveGrid":fhparse.PerspectiveGrid,"MpObject":fhparse.MpObject,"MString":fhparse.MString,"MList":fhparse.MList,"MDict":fhparse.MDict,\
				"DateTime":fhparse.DateTime,"FHDocHeader":fhparse.FHDocHeader,"Block":fhparse.Block,"Element":fhparse.Element,"BrushList":fhparse.BrushList,\
				"VMpObj":fhparse.VMpObj,"AGDFont":fhparse.VMpObj,   #fhparse.AGDFont,
				"FileDescriptor":fhparse.FileDescriptor,"TabTable":fhparse.TabTable,\
				"SymbolLibrary":fhparse.SymbolLibrary,"PropLst":fhparse.PropLst,"Procedure":fhparse.Procedure,"Color6":fhparse.Color6,"Data":fhparse.Data,\
				"MName":fhparse.MName,"List":fhparse.List,"LinePat":fhparse.LinePat,"ElemList":fhparse.ElemList,"ElemPropLst":fhparse.ElemPropLst,"Figure":fhparse.Figure,\
				"StylePropLst":fhparse.StylePropLst,"SpotColor6":fhparse.SpotColor6,"BasicLine":fhparse.BasicLine,"BasicFill":fhparse.BasicFill,\
				"Guides":fhparse.Guides,"Path":fhparse.Path,"Collector":fhparse.Collector,"Rectangle":fhparse.Rectangle,"Layer":fhparse.Layer,\
				"ArrowPath":fhparse.ArrowPath,"Group":fhparse.Group,"Xform":fhparse.Xform,"Oval":fhparse.Oval,"MultiColorList":fhparse.MultiColorList,\
				"ContourFill":fhparse.ContourFill,"ClipGroup":fhparse.ClipGroup,"NewBlend":fhparse.NewBlend,"BrushStroke":fhparse.BrushStroke,\
				"GraphicStyle":fhparse.GraphicStyle,"ContentFill":fhparse.ContentFill,"AttributeHolder":fhparse.AttributeHolder,\
				"FWShadowFilter":fhparse.FWShadowFilter,"FilterAttributeHolder":fhparse.FilterAttributeHolder,\
				"FWBevelFilter":fhparse.FWBevelFilter,"Extrusion":fhparse.Extrusion,"LinearFill":fhparse.LinearFill,\
				"CompositePath":fhparse.CompositePath,"GradientMaskFilter":fhparse.GradientMaskFilter,"DataList":fhparse.DataList,\
				"ImageImport":fhparse.ImageImport,"TextBlok":fhparse.TextBlok,"Paragraph":fhparse.Paragraph,"TString":fhparse.TString,\
				"LineTable":fhparse.LineTable,"TextColumn":fhparse.TextColumn,"RadialFillX":fhparse.RadialFillX,"TaperedFillX":fhparse.TaperedFillX,\
				"TintColor6":fhparse.TintColor6,"TaperedFill":fhparse.TaperedFill,"LensFill":fhparse.LensFill,"SymbolInstance":fhparse.SymbolInstance,\
				"BendFilter":fhparse.BendFilter, "TransformFilter":fhparse.TransformFilter,"NewContourFill":fhparse.NewContourFill,\
				"RaggedFilter":fhparse.RaggedFilter,"NewRadialFill":fhparse.NewRadialFill,"SketchFilter":fhparse.SketchFilter,\
				"ExpandFilter":fhparse.ExpandFilter,"ConeFill":fhparse.ConeFill, "DuetFilter":fhparse.DuetFilter, "TileFill":fhparse.TileFill,\
				"OpacityFilter":fhparse.OpacityFilter,"FWBlurFilter":fhparse.FWBlurFilter,"FWGlowFilter":fhparse.FWGlowFilter,"TFOnPath":fhparse.TFOnPath,\
				"CharacterFill":fhparse.CharacterFill,"FWFeatherFilter":fhparse.FWFeatherFilter, "PolygonFigure":fhparse.PolygonFigure,\
				"CalligraphicStroke":fhparse.CalligraphicStroke, "Envelope":fhparse.Envelope, "PathTextLineInfo":fhparse.PathTextLineInfo,\
				"PatternFill":fhparse.PatternFill,"FWSharpenFilter":fhparse.FWSharpenFilter,"RadialFill":fhparse.RadialFill,"SwfImport":fhparse.SwfImport,\
				"PerspectiveEnvelope":fhparse.PerspectiveEnvelope,"MultiBlend":fhparse.MultiBlend, "MasterPageElement":fhparse.MasterPageElement,\
				"MasterPageDocMan":fhparse.MasterPageDocMan,"MasterPageSymbolClass":fhparse.MasterPageSymbolClass, "MasterPageLayerElement":fhparse.MasterPageLayerElement,\
				"MQuickDict":fhparse.MQuickDict,"TEffect":fhparse.TEffect, "MasterPageSymbolInstance":fhparse.MasterPageSymbolInstance,\
				"MasterPageLayerInstance":fhparse.MasterPageLayerInstance, "TextInPath":fhparse.TextInPath, "ImageFill":fhparse.ImageFill,
				"CustomProc":fhparse.CustomProc, "ConnectorLine":fhparse.ConnectorLine, "PatternLine":fhparse.PatternLine,"PSLine":fhparse.PSLine,
				"Halftone":fhparse.Halftone,"AGDSelection":fhparse.AGDSelection}

ver = {0x31:5,0x32:7,0x33:8,0x34:9,0x35:10,0x36:11,'mcl':-1}

def fh_save (page, fname):
	model = page.view.get_model()
	f = open(fname,'w')
	endptr = 0
	iter1 = model.get_iter_first()
	iter1 = model.iter_next(iter1) # 'FH Header'
	value = model.get_value(iter1,3)
	f.write(value[:len(value)-4])
	epos = len(value)-16
#	endptr += len(value)-4
	iter2 = model.iter_next(iter1) # 'FH Decompressed data'
	value = ''
	clist = {}
	for i in range(model.iter_n_children(iter2)-1):
		citer = model.iter_nth_child(iter2,i)
		value += model.get_value(citer,3)
		rname = model.get_value(citer,0)
		clist[i] = rname[0:len(rname)-5]

	citer = model.iter_nth_child(iter2,i+1) # 'FH Tail'
	value += model.get_value(citer,3)
	output = zlib.compress(value,1)
	clen = struct.pack(">L",len(output)+12)

	f.write(clen)
	f.write(output)
	endptr += 4 + len(output) + 8
	
	dictsize = struct.pack('>h', len(page.dict))
	f.write(dictsize)
	f.write('\x02\x04') # points to some random record ID?
	endptr += 4
	cntlist = {}
#	for k, v in page.dict.items():  # not sure if FH pays attention to dict items sequence
#		f.write(struct.pack('>h',k))
#		f.write(v[0])
#		f.write('\x00')
#		cntlist[v[0]] = k
#		endptr += 3 + len(v[0])
	iter3 = model.iter_next(iter2) # 'FH Dictionary'
	for i in range(model.iter_n_children(iter3)):
		citer = model.iter_nth_child(iter3,i)
		value = model.get_value(citer,3)
		k = value[0:2]
		v = value[2:]
		f.write(k)
		f.write(v)
		v = v[:(len(v)-1)]
		cntlist[v] = k
		endptr += 3 + len(v)

	size = struct.pack('>L', model.iter_n_children(iter2)-1) # don't count tail
	f.write(size)
	endptr += 4
	for i in range(len(clist)):
		v = cntlist[clist[i]]
		f.write(v)
	endptr += len(clist)*2
	f.write('FlateDecode\x00\xFF\xFF\xFF\xFF\x1c\x09\x0a\x00\x04')
	endptr += 16
	f.write(struct.pack(">L",endptr))
	f.seek(epos)
	f.write(struct.pack(">L",endptr))
	f.close()



def fh_open (buf,page):
	page.dictmod = gtk.TreeStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
	iter1 = page.model.append(None,None)
	page.model.set_value(iter1,0,"FH file")
	page.model.set_value(iter1,1,("fh","file"))
	page.model.set_value(iter1,2,len(buf))
	page.model.set_value(iter1,3,buf)
	page.model.set_value(iter1,6,page.model.get_string_from_iter(iter1))

	offset = buf.find('AGD')
	page.version = ver[ord(buf[offset+3])]
	print 'Version:\t',page.version
	print 'Offset: \t%x'%offset
	[size] = struct.unpack('>L', buf[offset+8:offset+12])
	print 'Size:\t\t%x'%size
	iter1 = page.model.append(None,None)
	page.model.set_value(iter1,0,"FH Header")
	page.model.set_value(iter1,1,("fh","header"))
	page.model.set_value(iter1,2,offset+12)
	page.model.set_value(iter1,3,buf[:offset+12])
	page.model.set_value(iter1,6,page.model.get_string_from_iter(iter1))

	dditer = page.model.append(None,None)
	page.model.set_value(dditer,1,("fh","data"))
	if page.version > 8:
		output = zlib.decompress(buf[offset+14:offset+14+size],-15)
		page.model.set_value(dditer,0,"FH Decompressed Data")
		page.model.set_value(dditer,2,size)

	else:
		output = buf[offset+12:offset+size]
		page.model.set_value(dditer,0,"FH Data")
		page.model.set_value(dditer,2,size-12)

	offset = offset + size
	page.model.set_value(dditer,3,output)
	page.model.set_value(dditer,6,page.model.get_string_from_iter(dditer))

	dictiter = page.model.append(None,None)
	page.model.set_value(dictiter,0,"FH Dictionary")
	page.model.set_value(dictiter,1,("fh","dict"))
	page.model.set_value(dictiter,6,page.model.get_string_from_iter(dictiter))
	dictoffset = offset

	if page.version > 8:
		dictsize = struct.unpack('>h', buf[offset:offset+2])[0]
		print 'Dict size:\t%u'%dictsize
		offset+=4
		items = {}
		for i in range(dictsize):
			[key] = struct.unpack('>h', buf[offset:offset+2])
			k = 0
			while ord(buf[offset+k+2]) != 0:
				k+=1
			value = buf[offset+2:offset+k+2]
			niter = page.model.append(dictiter,None)
			page.model.set_value(niter,0,"%04x %s"%(key,value))
			page.model.set_value(niter,1,("fh","dval"))
			page.model.set_value(niter,2,k+3)
			page.model.set_value(niter,3,buf[offset:offset+k+3])
			page.model.set_value(niter,6,page.model.get_string_from_iter(niter))
			offset = offset+k+3
			items[key] = (value,0)
	else:
		offset,items = v8dict(buf,offset,dictiter,page)

	page.model.set_value(dictiter,2,offset-dictoffset)
	page.model.set_value(dictiter,3,buf[dictoffset:offset])
	page.dict = items

	size = struct.unpack('>L', buf[offset:offset+4])[0]
	print '# of items:\t%u'%size
	offset+= 4

	parser = fhparse.parser()
	parser.data = output
	parser.version = page.version
	parser.iter = dditer
	agdoffset = 0
	length = 0
	brflag = 0
	prkey = 0
	for i in range(size):
		if i/2000 == i/2000. and i > 0:
			print '\rRecord #%d'%i,items[key][0],len(parser.data)-agdoffset
		[key] = struct.unpack('>h', buf[offset:offset+2])
		offset+= 2
		if chunks.has_key(items[key][0]):
			if brflag == 0:
				try:
					length = chunks[items[key][0]](parser,agdoffset, key)
					if length < 0:
						length = len(output)-agdoffset
						brflag = 1
				except:
					print "Failed to parse. Chunk: %02x 2:%s"%(i,i-1)
					return
			else:
				length = 0
			iname = items[key][0]
			iter1 = page.model.append(dditer,None)
			page.model.set_value(iter1,0,"%s [%02x]"%(iname,i+1))
			page.model.set_value(iter1,1,("fh",iname))
			page.model.set_value(iter1,2,length)
			page.model.set_value(iter1,3,output[agdoffset:agdoffset+length])
			page.model.set_value(iter1,6,page.model.get_string_from_iter(iter1))
			agdoffset = agdoffset + length
			if brflag == 1:
				print "Negative length. Chunk: %02x 2:%s"%(i,i-1)
				brflag = 2
			
		else:
			print 'WARNING! Unknown key: ',items[key][0],"%02x %02x"%(i+1,agdoffset)
			iname = items[key][0]
			name = "%02x: "%(i+1)+" !!! " + iname+"\t0x%02x"%length+"\t0x%02x"%agdoffset+" <-------"
			iter1 = page.model.append(dditer,None)
			page.model.set_value(iter1,0,name)
			page.model.set_value(iter1,1,("fh","unknown"))
			page.model.set_value(iter1,2,1234)
			page.model.set_value(iter1,3,output[agdoffset:])
			page.model.set_value(iter1,6,page.model.get_string_from_iter(iter1))

	iter1 = page.model.append(dditer,None)
	page.model.set_value(iter1,0,"FH Tail")
	page.model.set_value(iter1,1,("fh","tail"))
	page.model.set_value(iter1,2,len(output)-agdoffset)
	page.model.set_value(iter1,3,output[agdoffset:])
	page.model.set_value(iter1,6,page.model.get_string_from_iter(iter1))



def str2hex(data):
	s = ''
	for i in range(len(data)):
		s+= '%02x '%ord(data[i])
	return s
	
def v8dict(buf,offset,parent,page):
	dictsize = struct.unpack('>h', buf[offset:offset+2])[0]
	lastkey = struct.unpack('>h', buf[offset+2:offset+4])[0]
	offset += 4
	print 'Dict size:\t%u, Last record: %04x'%(dictsize,lastkey)
	flag = 0
	keypaths = {"":None}
	items = {}
	for i in range(dictsize):
		key = struct.unpack('>h', buf[offset:offset+2])[0]
		key2 = struct.unpack('>h', buf[offset+2:offset+4])[0]
		offset += 4
		k = 0
		while ord(buf[offset+k]) != 0:
			k+=1
		value = buf[offset:offset+k]
		offset += k+1
		k = 0
		while flag != 2:
			while ord(buf[offset+k]) != 0:
				k+=1
			flag += 1
			k+=1
		flag = 0
		unkn = buf[offset:offset+k]
		offset+=k
		niter = page.model.append(parent,None)
		page.model.set_value(niter,0,"%04x %s"%(key,value))
		page.model.set_value(niter,1,("fh","dval"))
		page.model.set_value(niter,2,len(value)+len(unkn)+4)
		page.model.set_value(niter,3,buf[offset-len(value)-len(unkn)-5:offset])
		page.model.set_value(niter,6,page.model.get_string_from_iter(niter))


		items[key] = (value,unkn)
		piter = None
		if keypaths.has_key(key2):
			piter = keypaths[key2]
		d_iter = page.dictmod.append(piter,None)
		keypaths[key] = d_iter
		page.dictmod.set_value(d_iter,0,"%04x"%key)
		page.dictmod.set_value(d_iter,1,value)
		page.dictmod.set_value(d_iter,2,str2hex(unkn))

	return offset,items