#include "marfa.h"

#if defined(LIBJPEG_12_H)
// Including LIBJPEG_12_H preculdes libjpeg.h from being read again
CPL_C_START
#include LIBJPEG_12_H
CPL_C_END
#define  JPEG12_ON
#include "JPEG_band.cpp"
#endif

