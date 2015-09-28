#include <gdal.h>
#include <cpl_string.h>

// For C++ interface
#include <gdal_priv.h>
#include <../frmts/mrf/marfa.h>

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
        Resampling(SAMPLING_Avg),
        verbose(false),
        overlays(false)
    {};

    // Insert the target in the source, based on internal coordinates
    bool patch(void);

    void setTarget(const std::string &Target) 
        {TargetName=Target;}
    void setSource(const std::string &Source)
        {SourceName=Source;}
    void setResampling(const std::string &Resamp) {
	if (EQUALN(Resamp.c_str(), "Avg", 3))
	    Resampling = SAMPLING_Avg;
	else if (EQUALN(Resamp.c_str(), "NearNb", 6))
	    Resampling = SAMPLING_Near;
    }
    void setOverlays()
        {overlays=true; }
    void setProgress(GDALProgressFunc pfnProgress)
        {Progress=pfnProgress;}
    void setDebug(int level) 
        {verbose=level;}

private:
    int verbose;
    int overlays;
    std::string TargetName;
    std::string SourceName;
    int Resampling;
    GDALProgressFunc Progress;
};