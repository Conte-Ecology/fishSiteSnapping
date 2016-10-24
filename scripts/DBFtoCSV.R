library(foreign)


x <- read.dbf('C:/KPONEIL/streamNetwork/fishPoints/VTFWS.dbf')



out <- x[,c('SiteName', 'Latitude', 'Longitude', 'FEATUREID', 'HUC12')]


write.csv(out, file = 'C:/KPONEIL/streamNetwork/fishPoints/locationsCleaned_VTFWS.csv', row.names = F)
