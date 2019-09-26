;  the first seven are run as a batch check; same values for all
G1 X500 Y400; Test comment
G0 X500 y400 ;          Test comment
G10 X500 Y400 ;Test comment
G16 X500 Y400               ;
G01	X500	Y400  ; tabs in line
	G01 	 X500   	   Y400  ; tabs in line again
  g     1x   500 y    400  ; according to NIST this is valid gcode



; the following three require seperate checks
g0x +0. 1234y 7  ; actual example from NIST RS274 NGC Interpreter - V3
G01 X-5 Y-0.17
G17 Y0x500  ; make sure this is not handled as a hex

