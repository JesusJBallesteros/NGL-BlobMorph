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
    translate <0, 1.153822725, 7.707423094>
    scale <0.8710833827, 1.509536753, 0.8062974755>
    rotate <18.98645473, 0, 0>
  }
  sphere { <0, 0, 0>, 0.8, 1  // pair1
    translate <-0.9854726158, 0.8701271952, 7.474189701>
    scale <1.639154015, 0.6655755605, 0.7201143844>
    rotate <7.050528347, 25.07767813, 144.9314142>
  }
  sphere { <0, 0, 0>, 0.8, 1  // pair1_mirror
    translate <0.9854726158, 0.8701271952, 7.474189701>
    scale <1.639154015, 0.6655755605, 0.7201143844>
    rotate <7.050528347, -25.07767813, -144.9314142>
  }
  sphere { <0, 0, 0>, 0.8, 1  // mid2
    translate <0, -9.524870592, 21.21471575>
    scale <0.245760612, 0.3457232862, 0.2387859825>
    rotate <-32.55195318, 0, 0>
  }
}
object{ StimBlob
  rotate <0, 0, 0>
  translate <0, 0, 0>
  scale <1, 1, 1>
  pigment {White}
  finish { phong 0.0 ambient 0.4 diffuse 0.6 }
}
