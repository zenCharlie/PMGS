import statistics
import numpy as np
import netCDF4 
import PMG_Utilities as util
import datetime
EXTERNAL_CELL_ID_MINIMUM = 500000000
CANAL_MINIMUM = 300000
CANAL_MAXIMUM = 399999
class Transect_NetCDF:

	def __init__(self, filename):
		water_budget_nc = None
		water_budget_nc = netCDF4.Dataset(filename, 'r',format="NETCDF4_CLASSIC")
		locations = list(water_budget_nc.variables['locations'])
		self.coordinates = dict((int(i)-1, self.get_state_plane_coordinates(locations[int(j)])) \
			for i,j in water_budget_nc.variables['meshNodeMap'][:])
		tricons = list(water_budget_nc.variables['tricons'])
		self._tricons_concat = list()
		for i in range(len(tricons)):
				self._tricons_concat.append([tricons[i][0], tricons[i][1], tricons[i][2], tricons[i][0], tricons[i][1], tricons[i][2]])
		try:
			self._waterbodymap = list(water_budget_nc.variables['waterBodyMap'])
			waterMoverMap_Main = list()
			waterMoverMap_Main = list(water_budget_nc.variables['waterMoverMap'])
			self._watermovermap = {}
			self._external_cell_id_left = {}
			self._external_cell_id_right = {}
			for i in range(len( waterMoverMap_Main)):
						if int( waterMoverMap_Main[i][0]) >= EXTERNAL_CELL_ID_MINIMUM:
							key = int(waterMoverMap_Main[i][1])
							if key < EXTERNAL_CELL_ID_MINIMUM:
								if key not in self._external_cell_id_right:
									self._external_cell_id_right[key] = []
								self._external_cell_id_right[key].append(i)
						elif int( waterMoverMap_Main[i][1]) >= EXTERNAL_CELL_ID_MINIMUM:
							key = int(waterMoverMap_Main[i][0])
							if key < EXTERNAL_CELL_ID_MINIMUM:
								if key not in self._external_cell_id_left:
									self._external_cell_id_left[key] = []
								self._external_cell_id_left[key].append(i)
						else:
							key = (int( waterMoverMap_Main[i][0]), int(waterMoverMap_Main[i][1]))
							if key not in self._watermovermap:
								self._watermovermap[key] = []
							self._watermovermap[key].append(i)
			watermovertype = list(water_budget_nc.variables['waterMoverType'])
			self._watermovertype = []
			for i in range(len(watermovertype)):
				temp = []
				test = [w.decode("utf-8") for w in watermovertype[i]]
				for j in range(len(test)):
					temp.append(str(test[j][0]))
				self._watermovertype.append(''.join(temp).strip())
			watermovername = list(water_budget_nc.variables['waterMoverName'])
			self._watermovername = []
			for i in range(len(watermovername)):
				temp = []
				test_name = [w.decode("utf-8") for w in watermovername[i]]
				try:
					for j in range(len(test_name)):
						temp.append(test_name[j][0])
					self._watermovername.append(''.join(temp).strip())
				except Exception as e:
					print(e)
		except:
			pass
		try:
			self._watermovervolume = list()
			self._watermovervolume = list(water_budget_nc.variables['WaterMoverVolume'])
			self._watermovervolume_units = water_budget_nc.variables['WaterMoverVolume'].getncattr("units")
		except:
			self._watermovervolume = list()
			self._watermovervolume_units = water_budget_nc.variables['FMWatermovers'].getncattr("units")
			self._watermovervolume = list(water_budget_nc.variables['FMWatermovers'])
		self._timestamps = list(water_budget_nc.variables['timestamps'])
		timestamps = water_budget_nc.variables['timestamps']
		#date2 = nc.num2date(timestamps[:],units=timestamps.units.replace('24','00'))
		date, time = timestamps.units.split()[2:4]
		self._base_time = util.date_time_string(date, time)
		self._base_time_in_secs = util.time_to_seconds(date, time)
		self._time_fmt = '%m/%d/%Y %H:%M:%S'
		self._date_fmt = '%m/%d/%Y'
		print("inside Netcdf waterMoverMap_Main %d " % len(waterMoverMap_Main))
		print("inside Netcdf water_budget_nc.variables['waterMoverMap'] %d " % len(water_budget_nc.variables['waterMoverMap']))
		water_budget_nc.close()
		
		del waterMoverMap_Main
		del water_budget_nc

	def get_state_plane_coordinates(self, state_plane_coordinates):
		easting_x = float(state_plane_coordinates[0])
		northing_y = float(state_plane_coordinates[1])
		return easting_x, northing_y
	def getStartDate(self):
		return (self._base_time + datetime.timedelta(days=int(self._timestamps[0]))).strftime(self._date_fmt)
	def getEndDate(self):
		return (self._base_time + datetime.timedelta(days=int(self._timestamps[-1]))).strftime(self._date_fmt)
	def getTimestamp(self, i):
		return (self._base_time + datetime.timedelta(days=int(self._timestamps[i]))).strftime(self._time_fmt)
	def getTimestampLen(self):
		return len(self._timestamps)

if __name__ == "__main__":
	transect_netcdf = Transect_NetCDF("wbbudget.nc")
	print(transect_netcdf.getStartDate())

	transect_netcdf2 = Transect_NetCDF("wbbudget.nc")

	'''transect_netcdf2 = Transect_NetCDF("wbbudget.nc")
	transect_netcdf4 = Transect_NetCDF("wbbudget.nc")
	transect_netcdf6 = Transect_NetCDF("wbbudget.nc")
	transect_netcdf7 = Transect_NetCDF("wbbudget.nc")
	print(transect_netcdf7.getTimestampLen())'''