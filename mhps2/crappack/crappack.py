'''
	Open a file and try to pack or unpack it
	Released to the public domain
	2017 the_fog
'''

import pygtk
pygtk.require('2.0')
import gtk
import sys, os, struct
from array import array

def searchsequence(s, sptr):
	if sptr >= len(s):
		return (2, 0, 0)
	if sptr <= 0:
		return (0, 0, 0)

	# set boundary for sequence
	maxoffset = sptr
	if sptr > 0x7ff:
		maxoffset = 0x7ff

	off_max = 0
	len_max = 0
	off = 1
	while off < maxoffset:
		# first byte matches, it's a candidate for the sequence
		if s[sptr-off]==s[sptr]:
			# how long is it ?
			clen = 0
			while s[sptr-off+clen]==s[sptr+clen] and (sptr+clen+1)<len(s):
				clen = clen + 1

			# only keep the longest possible sequence
			if clen > len_max:
				len_max = clen
				off_max = off

		off = off + 1

	if len_max > 1:
		return (1, off_max, len_max)
	else:
		return (0, 0, 0)


def sldpack(t):
	# convert to halfword array
	src = []
	if (len(t)&1)==1:
		t = ''.join([t, '\x00'])
	for i in range(len(t)>>1):
		o = i*2
		src.append(struct.pack("<H", struct.unpack("<H", t[o:o+2])[0]))

	dst = []
	srcptr = 0
	dstptr = 0
	while srcptr < len(src):
		seq = 0
		seqptr = dstptr
		dst.append(struct.pack("<H", 0))
		dstptr = dstptr + 1
		# create the command word (16 bit 2 bytes)
		for i in range(16):
			r, offset, length = searchsequence(src, srcptr)
			# end of file
			if r==2:
				dst[seqptr] = struct.pack("<H", struct.unpack("<H", dst[seqptr])[0] | (1<<(15-i)))
				dst.append(struct.pack("<HH", 0, 0))
				i = 16

			# store offset
			if r==1:
				# does the found sequence length fit in one word together with offset?
				if length <= 0x1f:
					dst.append(struct.pack("<H", (length << 11) | (offset & 0x07ff)))
					dstptr = dstptr + 1
				else:
					dst.append(struct.pack("<2H", offset & 0x07ff, length))
					dstptr = dstptr + 1
							   
				srcptr = srcptr + length
				# set sequence information to "copy length bytes from offset"
				dst[seqptr] = struct.pack("<H", struct.unpack("<H", dst[seqptr])[0] | (1<<(15-i)))

			# copy bytes
			else:
				if srcptr < len(src):
					dst.append(src[srcptr])
				dstptr = dstptr + 1
				srcptr = srcptr + 1

	return ''.join(dst)


def sldunpack(t):
	sptr = 0
	dptr = 0
	d = array('B')

	while sptr < len(t):
		m = 0x8000
		c = struct.unpack("<H", t[sptr:sptr+2])[0]
		sptr += 2

		while m > 0:
			if c & m:
				s = struct.unpack("<H", t[sptr:sptr+2])[0]
				sptr += 2
				o = (s & 0x07ff) * 2
				l = ((s >> 11) & 0x1f) * 2

				if l > 0:
					for x in range(l):
						d.append(d[dptr-o])
						dptr += 1

				else:
					s = struct.unpack("<H", t[sptr:sptr+2])[0]
					sptr += 2
					l = s * 2
					for x in range(l):
						d.append(d[dptr-o])
						dptr += 1
			else:
				if sptr+2 < len(t):
					d.append(struct.unpack("B", t[sptr:sptr+1])[0])
					d.append(struct.unpack("B", t[sptr+1:sptr+2])[0])
				sptr += 2
				dptr += 2

			m >>= 1

	return d


class CrapPack(object):
	def unpack_clicked(self, widget, event, data=None):
		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		filter = gtk.FileFilter()
		filter.set_name("all files")
		filter.add_pattern("*")
		chooser.add_filter(filter)

		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			f = open(chooser.get_filename(), 'rb')
			b = f.read()
			f.close()

			b = sldunpack(b)
			f = open(chooser.get_filename() + ".unpacked", "wb")
			f.write(b)
			f.close()
		elif response == gtk.RESPONSE_CANCEL:
			pass
		chooser.destroy()


	def pack_clicked(self, widget, event, data=None):
		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		filter = gtk.FileFilter()
		filter.set_name("all files")
		filter.add_pattern("*")
		chooser.add_filter(filter)

		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			f = open(chooser.get_filename(), 'rb')
			b = f.read()
			f.close()

			b = sldpack(b)
			f = open(chooser.get_filename() + ".packed", "wb")
			f.write(b)
			f.close()
		elif response == gtk.RESPONSE_CANCEL:
			pass
		chooser.destroy()

	def destroy(self, widget, data=None):
		gtk.main_quit()

	def __init__(self):
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

		#signals
		self.window.connect("destroy", self.destroy)
		self.window.connect("delete_event", self.destroy)

		#hbox for the buttons
		self.hbox = gtk.HBox(False, 0)

		#buttons
		self.button = gtk.Button("unpack")
		self.button.connect("clicked", self.unpack_clicked, None)
		self.hbox.pack_start(self.button, False, False, 0)
		self.button.show()

		self.button2 = gtk.Button("pack")
		self.button2.connect("clicked", self.pack_clicked, None)
		self.hbox.pack_start(self.button2, False, False, 0)
		self.button2.show()

		#finally showing stuff
		self.window.add(self.hbox)
		self.hbox.show()

		self.window.show()

	def main(self):
		gtk.main()

if __name__ == '__main__':
	app = CrapPack()
	app.main()
