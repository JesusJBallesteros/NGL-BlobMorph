#version 3.6;
#include "colors.inc"
background{Black}
camera {
  angle 15
  right <1.747163695,0,0>
  location <0, 0, -11>
  look_at <0, 0, 0>
}
light_source { <0, -10, -10> color White }
#declare StimBlob = blob {
  threshold 0.2
  sphere { <0, 0, 0>, 0.8, 1  // mid0
    translate <0, -9.792995561, 2.659508196>
    scale <1.167208486, 0.5635569888, 1.405368038>
    rotate <-51.09453173, 0, 0>
  }
  sphere { <0, 0, 0>, 0.8, 1  // pair1
    translate <0.5056953754, 2.161530204, 7.4458965>
    scale <1.718764972, 1.451643286, 0.548852765>
    rotate <42.57755714, -7.446325537, -175.6298567>
  }
  sphere { <0, 0, 0>, 0.8, 1  // pair1_mirror
    translate <-0.5056953754, 2.161530204, 7.4458965>
    scale <1.718764972, 1.451643286, 0.548852765>
    rotate <42.57755714, 7.446325537, 175.6298567>
  }
  sphere { <0, 0, 0>, 0.8, 1  // mid2
    translate <0, -5.851549115, 20.85617002>
    scale <0.2023938221, 0.4805464238, 0.2175687478>
    rotate <-23.79979003, 0, 0>
  }
  sphere { <0, 0, 0>, 0.8, 1  // pair3
    translate <-10.23163976, -2.872095508, 33.74070731>
    scale <0.1939383268, 0.8243810732, 0.1724893455>
    rotate <-17.39144186, 13.32201829, 10.4573223>
  }
  sphere { <0, 0, 0>, 0.8, 1  // pair3_mirror
    translate <10.23163976, -2.872095508, 33.74070731>
    scale <0.1939383268, 0.8243810732, 0.1724893455>
    rotate <-17.39144186, -13.32201829, -10.4573223>
  }
}
object{ StimBlob
  rotate <0, 0, 0>
  translate <0, 0, 0>
  scale <1, 1, 1>
  pigment {White}
  finish { phong 0.0 ambient 0.4 diffuse 0.6 }
}
