import arcpy
from arcpy import env
from arcpy.sa import *

# ==============
# Specify inputs
# ==============
networkGrid_DEM       = "C:/KPONEIL/delineation/northeast/arcHydroFiles/Layers/strdem"
networkGrid_Detailed  = "C:/KPONEIL/delineation/northeast/arcHydroFiles/arcHydroFiles.gdb/strHR"
networkGrid_Truncated = "C:/KPONEIL/delineation/northeast/arcHydroFiles/Layers/str"

points = "C:/KPONEIL/streamNetwork/fishPoints/fishPoints.gdb/locations_VT"

version = "VTFS"

bufferInMeters = "100"

workingDirectory = "C:/KPONEIL/streamNetwork/occupancy/networkAnalysis.gdb"


# ==================
# Streams processing
# ==================

# Copy the layers to the working directory
# ----------------------------------------
# This step is taken because of column naming methods in sampling.

# DEM
demPath = workingDirectory + "/flowDem"
if not arcpy.Exists(demPath):
	dem = arcpy.CopyRaster_management(networkGrid_DEM,
									   demPath,
									   "", "","","","","8_BIT_SIGNED")
else: dem = demPath

# Detailed streams
detailedPath = workingDirectory + "/flowDetailed"
if not arcpy.Exists(detailedPath):
	detailed = arcpy.CopyRaster_management(networkGrid_Detailed,
											detailedPath,
											"", "","","","","8_BIT_SIGNED")
else: detailed = detailedPath										   
		
# Truncated streams
truncatedPath = workingDirectory + "/flowTruncated"
if not arcpy.Exists(truncatedPath):		
	truncated = arcpy.CopyRaster_management(networkGrid_Truncated,
											   truncatedPath,
											   "", "","","","","8_BIT_SIGNED")
else: truncated = truncatedPath											   

# Observed points
observedPath = workingDirectory + "/samplePoints_" + version
if not arcpy.Exists(observedPath):	
	observed = arcpy.FeatureClassToFeatureClass_conversion(points, 
															workingDirectory, 
															"samplePoints_" + version)
else: observed = observedPath	

# Mosaic rasters
if not arcpy.Exists(workingDirectory + "/flowMosaic"):	
	mosaicFlowGrid = arcpy.MosaicToNewRaster_management([dem, detailed],
															workingDirectory, 
															"flowMosaic",
															detailed,
															"8_BIT_SIGNED", 
															30, 
															1, 
															"MAXIMUM",
															"FIRST")
else: mosaicFlowGrid = workingDirectory + "/flowMosaic"
										
# Convert the mosaicked flow grid to a polyline so the points can be snapped to it
if not arcpy.Exists(workingDirectory + "/vectorMosaic"):	
	mosaicFlowLines  = arcpy.RasterToPolyline_conversion(mosaicFlowGrid, 
															workingDirectory + "/vectorMosaic", 
															"NODATA",
															"", 
															"NO_SIMPLIFY")
else: mosaicFlowLines = workingDirectory + "/vectorMosaic"

# ==========================		
# Observed points processing
# ==========================
# Make a feature layer of the observed points so it can be processed
arcpy.MakeFeatureLayer_management(observed, "pointsLyr")														
														
# Snap the points to the flowlines
arcpy.Snap_edit("pointsLyr", 
					[[mosaicFlowLines, "EDGE", bufferInMeters + " Meters"]])
					
# Sample the different versions of flow grids so the points can be classified. The points now lie on these grids after snapping
sampleOutput = Sample([dem, detailed, truncated], 
								"pointsLyr",
								workingDirectory + "/sampleTable_" + version,
								"NEAREST")					
								
# Calculate the field that described the location
arcpy.AddField_management("pointsLyr", "LocationClass", "TEXT")														
		
# Join the sample table to the points layer so the points can be classified
arcpy.JoinField_management("pointsLyr", 
							"OBJECTID", 
							sampleOutput, 
							"samplePoints_" + version, 
							["flowDem", "flowDetailed", "flowTruncated"])

							

# Classify points
# ---------------
# Points outside of the snapping limit
arcpy.SelectLayerByAttribute_management ("pointsLyr", 
											"NEW_SELECTION", 
											""" flowDetailed IS NULL AND flowDem IS NULL AND flowTruncated IS NULL """)										
arcpy.CalculateField_management ("pointsLyr", "LocationClass", """ "Outside """ + bufferInMeters + """ Meter Buffer" """)

# Points not on our flowlines, but within buffer of DEM derived streams
arcpy.SelectLayerByAttribute_management ("pointsLyr", 
											"NEW_SELECTION", 
											""" flowDetailed IS NULL AND flowDem = 1 AND flowTruncated IS NULL """)
arcpy.CalculateField_management ("pointsLyr", "LocationClass", """ "Undocumented Stream" """)	

# Points that only fall on the "deatiled" flow network
arcpy.SelectLayerByAttribute_management ("pointsLyr", 
											"NEW_SELECTION", 
											""" flowDetailed = 1 AND flowTruncated IS NULL """)
arcpy.CalculateField_management ("pointsLyr", "LocationClass", """ "Detailed Network Only" """)	

# Points that fall on the "truncated" network
arcpy.SelectLayerByAttribute_management ("pointsLyr", 
											"NEW_SELECTION", 
											""" flowTruncated = 1 """)
arcpy.CalculateField_management ("pointsLyr", "LocationClass", """ "Truncated Network" """)	

# Points that were missed 
arcpy.SelectLayerByAttribute_management ("pointsLyr", 
											"NEW_SELECTION", 
											""" LocationClass IS NULL """)
arcpy.CalculateField_management ("pointsLyr", "LocationClass", """ "Unclassified" """)	
	
								
# Output summary statistics of where points fall						
arcpy.Statistics_analysis("pointsLyr", 
							workingDirectory + "/snappedStats_" + version, [["LocationClass", "COUNT"]], "LocationClass")							


# Save the snapped points (feature layer is temporary)
arcpy.SelectLayerByAttribute_management ("pointsLyr", "CLEAR_SELECTION")
arcpy.SelectLayerByAttribute_management ("pointsLyr", "SWITCH_SELECTION")

arcpy.CopyFeatures_management("pointsLyr", 
								workingDirectory + "/snappedPointsDetailed_"  + version)

arcpy.SelectLayerByAttribute_management ("pointsLyr", "CLEAR_SELECTION")
