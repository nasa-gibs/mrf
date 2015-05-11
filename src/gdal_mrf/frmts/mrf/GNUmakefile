# Modified for MRF plugin

include ../../GDALmake.opt

FILES	=	marfa_dataset mrf_band JPEG_band PNG_band Raw_band Tif_band mrf_util mrf_overview
OBJ 	=	$(addsuffix .o, $(FILES))
LO_O_OBJ	=	$(addsuffix .lo,$(basename $(O_OBJ)))

ifneq ("$(wildcard LERC_band.cpp)","")
FILES	:= LERC_band RLE BitMask BitStuffer CntZImage $(FILES)
CPPFLAGS := -DLERC
endif

CPPFLAGS	:= -fPIC $(GDAL_INCLUDE) $(CPPFLAGS)

default:	$(OBJ:.o=.$(OBJ_EXT))

clean:
	rm -rf *.o *.lo .libs/$(OBJ) .libs $(O_OBJ) $(LO_O_OBJ) gdal_mrf.so.1

install-obj:	$(O_OBJ:.o=.$(OBJ_EXT))

$(OBJ) $(O_OBJ):	marfa.h

plugin: $(OBJ)
	g++ -shared -W1,-soname,gdal_mrf.so.1 $(OBJ) -o gdal_mrf.so.1

iplugin: gdal_mrf.so.1 plugin
	cp $< $(prefix)/lib/gdalplugins/1.9/$<
