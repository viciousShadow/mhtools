# -*- coding: utf-8 -*-

'''
	Little helper for translation of .bin files
	Monster Hunter Dos PS2
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



class Test(object):
	def loadtrn(self, fname, lalista):
		lalista.clear()
		f = open(fname, 'rb')
		cnt = struct.unpack("<L", f.read(4))[0]
		for i in range(cnt):
			r0, r1, r2l, r3l = struct.unpack("<4L", f.read(4*4))
			r2 = f.read(r2l)
			r3 = f.read(r3l)
			lalista.append([r0, r1, r2, r3])
		f.close()

	def savetrn(self, fname, lalista):
		f = open(fname, 'wb')
		f.write(struct.pack("<L", len(lalista)))
		for row in lalista:
			head = struct.pack("<4L", row[0], row[1], len(row[2]), len(row[3]))
			f.write(head)
			f.write(row[2])
			f.write(row[3])
		f.close()


	def getstring(self, lalista, cid, stid):
		for row in lalista:
			if row[0]==cid and row[1]==stid:
				if row[3] <> '':
					return(row[3] + '\x00')
				# not translated, use the original code
				return (row[2].encode('shift-jis') + '\x00')

	# create a packed bin from the translated list
	def savelist(self, fname, lalista):
		# create cids-array with the cids and the amount of strings in each cid
		cids = []
		cid = 0
		for row in lalista:
			if row[0]<>cid:
				cid = row[0]
				stid = 0
				for row2 in lalista:
					if row2[0]==cid and row2[1]>stid:
						stid = row2[1]
				cids.append([cid, stid])

		d = []
		ptr = 0
		# the header
		for cid in cids:
			d.append(struct.pack("<2L", 0, 0))
			ptr = ptr + 8
		d.append(struct.pack("<2L", 0xffffffff, 0xffffffff))
		ptr = ptr + 8

		cnr = 0
		for cid, stid in cids:
			d[cnr] = struct.pack("<2L", cid, ptr)
			# chunk header
			stnr = len(d)
			cptr = 0
			for i in range(1, stid+1):
				d.append(struct.pack("<L", 0))
				ptr = ptr + 4
				cptr = cptr + 4
			# strings
			for i in range(1, stid+1):
				d[stnr] = struct.pack("<L", cptr)
				st = self.getstring(lalista, cid, i)
				d.append(st)
				ptr = ptr + len(st)
				cptr = cptr + len(st)
				stnr = stnr + 1
			d.append('\x00')
			ptr = ptr + 1
			cnr = cnr + 1

		d = ''.join(d)
		# finally save everything
		f = open(fname, 'wb')
		f.write(sldpack(d))
		f.close()


	# open a bin, interpret data and show some list for translation
	def createlist(self, fname, lalista):
		f = open(fname, 'rb')
		d = sldunpack(f.read())
		f.close()

		lalista.clear()

		# read chunk ids and offsets
		dlist=[]
		offset = 0
		did = 0
		doff = 0
		while(did <> 0xffffffff):
			did, doff = struct.unpack("<LL", d[offset:offset+8])
			dlist.append([did, doff])
			offset = offset + 8

		# now reads chunk
		for i in range(len(dlist)-1):
			did, doff = dlist[i]
			stlen=1
			n = 0
			stid = 1
			while stlen > 0:
				stoff  = doff + struct.unpack("<L", d[doff+n:doff+n+4])[0]
				stlen = 0
				while d[stoff+stlen] <> 0:
					stlen = stlen+1
				stlen = stlen + 1
				if stlen >0:
					st = struct.unpack("%ds" % stlen, d[stoff:stoff+stlen])
					st = ''.join(st)
					lalista.append([did, stid, st.decode('shift-jis'), ''])
					n = n + 4
					stid = stid + 1
					if struct.unpack("<L", d[doff+n:doff+n+4])[0] > 10240:
						stlen = -1


	def loadbin_clicked(self, widget, event, data=None):
		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		filter = gtk.FileFilter()
		filter.set_name("all files")
		filter.add_pattern("*")
		chooser.add_filter(filter)

		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			self.createlist(chooser.get_filename(), self.liststore)
			print chooser.get_filename(), 'selected for loading'
		elif response == gtk.RESPONSE_CANCEL:
			print 'Closed, no files selected'
		chooser.destroy()

	def loadtrn_clicked(self, widget, event, data=None):
		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		filter = gtk.FileFilter()
		filter.set_name("all files")
		filter.add_pattern("*")
		chooser.add_filter(filter)

		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			self.loadtrn(chooser.get_filename(), self.liststore)
			print chooser.get_filename(), 'selected for loading'
		elif response == gtk.RESPONSE_CANCEL:
			print 'Closed, no files selected'
		chooser.destroy()

	def savetrn_clicked(self, widget, event, data=None):
		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		filter = gtk.FileFilter()
		filter.set_name("all files")
		filter.add_pattern("*")
		chooser.add_filter(filter)

		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			self.savetrn(chooser.get_filename(), self.liststore)
			print chooser.get_filename(), 'selected for saving'
		elif response == gtk.RESPONSE_CANCEL:
			print 'Closed, no files selected'
		chooser.destroy()


	def savebin_clicked(self, widget, event, data=None):
		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		filter = gtk.FileFilter()
		filter.set_name("all files")
		filter.add_pattern("*")
		chooser.add_filter(filter)

		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			self.savelist(chooser.get_filename(), self.liststore)
			print chooser.get_filename(), 'selected for saving'
		elif response == gtk.RESPONSE_CANCEL:
			print 'Closed, no files selected'
		chooser.destroy()


	def destroy(self, widget, data=None):
		gtk.main_quit()

	def edited_cb(self, cell, path, new_text, user_data):
		liststore, column = user_data
		liststore[path][column] = new_text

	def __init__(self):
		#liststore for the texts
		self.liststore = gtk.ListStore(int, int, str, str)

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

		#signals
		self.window.connect("destroy", self.destroy)
		self.window.connect("delete_event", self.destroy)

		#vbox for organizing vertically
		self.vbox = gtk.VBox(False, 0)

		#hbox for the buttons
		self.hbox = gtk.HBox(False, 0)

		#buttons
		self.button = gtk.Button("Load BIN")
		self.button.connect("clicked", self.loadbin_clicked, None)
		self.hbox.pack_start(self.button, False, False, 0)
		self.button.show()

		self.button2 = gtk.Button("Load TRN")
		self.button2.connect("clicked", self.loadtrn_clicked, None)
		self.hbox.pack_start(self.button2, False, False, 0)
		self.button2.show()

		self.button3 = gtk.Button("Save TRN")
		self.button3.connect("clicked", self.savetrn_clicked, None)
		self.hbox.pack_start(self.button3, False, False, 0)
		self.button3.show()

		self.button4 = gtk.Button("Save BIN")
		self.button4.connect("clicked", self.savebin_clicked, None)
		self.hbox.pack_start(self.button4, False, False, 0)
		self.button4.show()

		self.hbox.show()
		self.vbox.pack_start(self.hbox, False)

		#treeview to show and edit the list
		self.treeview = gtk.TreeView(model=self.liststore)
		self.treeview.set_headers_visible(True)
		self.treeview.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
		cell = gtk.CellRendererText()
		cell.set_property('editable', True)
		col1 = gtk.TreeViewColumn('chunk', cell, text=0)
		col2 = gtk.TreeViewColumn('number', cell, text=1)
		col3 = gtk.TreeViewColumn('japanaese', cell, text=2)

		cell = gtk.CellRendererText()
		cell.set_property('editable', True)
		col4 = gtk.TreeViewColumn('translated', cell, text=3)
		cell.connect('edited', self.edited_cb, (self.liststore,3))

		self.treeview.append_column(col1)
		self.treeview.append_column(col2)
		self.treeview.append_column(col3)
		self.treeview.append_column(col4)

		self.treeview.show()
		self.scw = gtk.ScrolledWindow()
		self.scw.add_with_viewport(self.treeview)
		self.scw.show()
		self.vbox.pack_start(self.scw)

		#finally showing stuff
		self.window.add(self.vbox)
		self.vbox.show()

		self.window.show()

	def main(self):
		gtk.main()

if __name__ == '__main__':
	app = Test()
	app.main()
