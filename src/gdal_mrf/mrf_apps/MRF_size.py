#-------------------------------------------------------------------------------
# Name:        MRF_size
# Purpose:     Visualize an MRF size index content
#
# Author:      luci6974
#
# Created:     30/07/2015
# Copyright:   (c) luci6974 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

'''Builds a GDAL vrt that visualizes the size of tiles in an MRF index'''
#
# Only trivial MRFs for now, flat files, default index name. Should be extended
# to support all MRFs
#
# It creates a gdal VRT file with a pixel per tile, where the pixel value
# is the size of the respective tile
# This is very useful to understand the state of an MRF
# Since most tiles are compressed, the size of the tile tends to be proportional
# to the entropy (information) of the data within the tile.
#

import xml.etree.ElementTree as XML
import sys
import os.path as path

def usage():
    print 'Takes one argument, an MRF file name, ' +\
        'builds a .vrt that contains the tile size info'

def XMLprettify(elem, level=0):
    'XML prettifier'
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            XMLprettify(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class PointXYZC(object):
    'Four value'
    def __init__(self, node, defaults = (-1, -1, 1, 1)):
        try:
            self.x = int(node.attrib['x'])
        except:
            self.x = defaults[0]
        try:
            self.y = int(node.attrib['y'])
        except:
            self.y = defaults[1]
        try:
            self.z = int(node.attrib['z'])
        except:
            self.z = defaults[2]
        try:
            self.c = int(node.attrib['c'])
        except:
            self.c = defaults[3]

    def __str__(self):
        f = "PointXYZC ({self.x}, {self.y}, {self.z}, {self.c})"
        return f.format(self=self)

class BBOX(object):
    'Four value'
    def __init__(self, node):
        self.minx = float(node.attrib['minx'])
        self.maxx = float(node.attrib['maxx'])
        self.miny = float(node.attrib['miny'])
        self.maxy = float(node.attrib['maxy'])

    def __str__(self):
        f = "BBOX ({self.minx}, {self.miny}, {self.maxx}, {self.maxy})"
        return f.format(self=self)

class MRF(object):
    'MRF metadata reader'
    def __init__(self, name):
        try:
            root = XML.parse(name).getroot()
        except:
            raise Exception, "Can't parse " + name

        if root.tag != 'MRF_META':
            raise Exception, name + ' is not an MRF metadata file'

        self.name = name
        #Get the basic raster info
        self.size = PointXYZC(root.find('Raster/Size'))
        self.pagesize = PointXYZC(root.find('Raster/PageSize'),
            (512, 512, 1, self.size.c))
        self.projection = root.find('GeoTags/Projection').text
        self.bbox = BBOX(root.find('GeoTags/BoundingBox'))

    def geotransform(self):
        'gdal style affine geotransform as a list'
        return [self.bbox.minx, (self.bbox.maxx - self.bbox.minx)/self.size.x, 0,
            self.bbox.maxy, 0, (self.bbox.miny - self.bbox.maxy)/self.size.y]

def VRT_Size(mrf):
    'Builds and returns a gdal VRT XML tree'
    xsz = 1 + (mrf.size.x-1)/mrf.pagesize.x
    ysz = 1 + (mrf.size.y-1)/mrf.pagesize.y
    root = XML.Element('VRTDataset', {
        'rasterXSize':str(xsz),
        'rasterYSize':str(ysz)
        })
    XML.SubElement(root,'SRS').text = mrf.projection
    gt = mrf.geotransform()
    # Adjust for pagesize
    gt[1] *= mrf.pagesize.x
    gt[5] *= mrf.pagesize.y
    XML.SubElement(root,'GeoTransform').text = ",".join(( str(x) for x in gt))
    bands = mrf.size.c / mrf.pagesize.c
    for band in range(bands):
        xband = XML.SubElement(root, 'VRTRasterBand', {
            'band':str(band+1),
            'dataType':'UInt32',
            'subClass':'VRTRawRasterBand'
            })
        idxname = path.splitext(path.basename(mrf.name))[0] + '.idx'
        XML.SubElement(xband,'SourceFilename', { 'relativetoVRT':"1" }).text =\
            idxname
        XML.SubElement(xband,'ImageOffset').text = str(12 + 16 * band)
        XML.SubElement(xband,'PixelOffset').text = str(16 * bands)
        XML.SubElement(xband,'LineOffset').text = str(16 * xsz * bands)
        XML.SubElement(xband,'NoDataValue').text = '0'
        XML.SubElement(xband,'ByteOrder').text = 'MSB'

    return XML.ElementTree(root)

def main():
    if (len(sys.argv) != 2):
        usage()
        return
    name = sys.argv[1]
    outname = path.splitext(name)[0] + '_size.vrt'
    vrt = VRT_Size(MRF(name))
    XMLprettify(vrt.getroot())
    vrt.write(outname)

if __name__ == '__main__':
    main()