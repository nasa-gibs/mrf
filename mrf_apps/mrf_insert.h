/*
* Copyright (c) 2002-2015, California Institute of Technology.
* All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
* Redistribution and use in source and binary forms, with or without modification, are permitted provided
* that the following conditions are met:
*   1. Redistributions of source code must retain the above copyright notice, this list of conditions and
*      the following disclaimer.
*   2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
*      the following disclaimer in the documentation and/or other materials provided with the distribution.
*   3. Neither the name of the California Institute of Technology (Caltech), its operating division the
*      Jet Propulsion Laboratory (JPL), the National Aeronautics and Space Administration (NASA),
*      nor the names of its contributors may be used to endorse or promote products derived from this software
*      without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
* INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
* IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
* EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
* STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*
* Copyright 2015 Esri
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

#include <gdal.h>
#include <cpl_string.h>

// For C++ interface
#include <gdal_priv.h>
#include <frmts/mrf/marfa.h>

#include <vector>
#include <string>

// generic bounds
struct Bounds {
    double lx,ly,ux,uy;
};

std::ostream& operator<<(std::ostream &out, const Bounds& sz)
{
    out << "lx=" << sz.lx << ",ly=" << sz.ly 
        << ",ux=" << sz.ux << ",uy=" << sz.uy ;
    return out;
};

// Location
struct XY {
    double x,y;
};

struct img_info {
    img_info(GDALDatasetH hDS);
    Bounds bbox;
    XY size;
    XY res;
};

class state {

public:
    state():Progress(GDALTermProgress),
        Resampling(GDAL_MRF::SAMPLING_Avg),
        verbose(false),
        overlays(false),
	start_level(0), // From begining
	stop_level(-1)  // To end
    {};

    // Insert the target in the source, based on internal coordinates
    bool patch(void);

    void setStart(int level) { start_level = level; }

    void setStop(int level) { stop_level = level; }

    void setTarget(const std::string &Target) {TargetName=Target;}

    void setSource(const std::string &Source) {SourceName=Source;}

    void setOverlays() { overlays = true; }

    void setProgress(GDALProgressFunc pfnProgress) { Progress = pfnProgress; }

    void setDebug(int level) { verbose = level; }

    void setResampling(const std::string &Resamp) {
	if (EQUALN(Resamp.c_str(), "Avg", 3))
	    Resampling = GDAL_MRF::SAMPLING_Avg;
	else if (EQUALN(Resamp.c_str(), "NearNb", 6))
	    Resampling = GDAL_MRF::SAMPLING_Near;
    }

private:
    int verbose;
    int overlays;
    int start_level;
    int stop_level;
    std::string TargetName;
    std::string SourceName;
    int Resampling;
    GDALProgressFunc Progress;
};
