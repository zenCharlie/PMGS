import os
import sys
import time
import re
import numpy as np
import getpass
import math
import statistics
import traceback 
from PMGTransect_NETCDF import Transect_NetCDF
import PMG_Data 
import PMG_Utilities as util
from PMG_Exceptions import TransectProccessErrorMessage
from PMGTransect_Output import ReportType, ProcessData, CSVOutput
from PMGTransect_Timing import Transect_Timing_Process, Timing_Data
from PMG_Graphics import PMG_Transect_Timing, PMG_Transect_Continuity
from PMGTransect_Continuity import Transect_Continuity_Process, Continuity_Data, COV_THRESHOLD

CANAL_MINIMUM = 300000
CANAL_MAXIMUM = 399999
TIME_MAX = 5
print_count = 100
COLUMN_WIDTH = 20
DECIMAL_PLACES = 5
SECS_PER_DAY = 86400.0
TIME_MAX = 5

class LocalData:
	def __init__(self, netCDF_file, nodelist, seepage_report_list, \
		report_type_list, savedir=None, savelabel=None, segment_list=None) -> None:
		self.netCDF_file = netCDF_file
		self.nodelist = nodelist
		self.seepage_report_list = seepage_report_list
		self.report_type_list = report_type_list
		self.savedir = savedir
		self.savelabel = savelabel
		self.segmentlist = segment_list

class TransectTool:
	def __init__(self, local_data):
		self.local_data = local_data
		self.nc = Transect_NetCDF(local_data.netCDF_file)



	def get_adjacent_watermovers(self, watermover):
		adjacent_watermovers = []
		(left, right) = watermover
		for key in self.nc._watermovermap.keys():
			if left in key or right in key:
				(key_left, key_right) = key
				if (key_left >= CANAL_MINIMUM and key_right <= CANAL_MAXIMUM) or \
				(key_right >= CANAL_MINIMUM and key_right <= CANAL_MAXIMUM):
					adjacent_watermovers.append(key)
		return adjacent_watermovers

	def get_seasonal_data(self, seasonal_data_parameters):
		seasonal_data = []
		for seasonal_data_parameter in seasonal_data_parameters:
			(group, month1_option, day1_option, month2_option, day2_option) = seasonal_data_parameter
			month1 = month1_option.index(0)+1
			day1 = day1_option.index(0)+1
			month2 = month2_option.index(0)+1
			day2 = day2_option.index(0)+1
			seasonal_data.append((month1, day1, month2, day2))
		return seasonal_data

	def in_monthly_range(self, dates, month, day):
			(month1, day1, month2, day2) = dates
			if month1 <= month2:
				if month > month1 and month < month2:
					return True
				elif month == month1 and month < month2:
					if day >= day1:
						return True
					else:
						return False
				elif month == month1 and month == month2:
					if day >= day1 and day <= day2:
						return True
					elif day1 > day2 and day <= day2:
						return True
					else:
						return False
				elif month == month2:
					if day <= day2:
						return True
					else:
						return False
				else:
					return False
			else: # month1 > month2:
				if month > month1 or month < month2:
					return True
				elif month == month1 and day >= day1:
					return True
				elif month == month2 and day <= day2:
					return True
				else:
					return False

	def timestamp_loop(self, message, watermovers, segment_watermovers, data, outputfile, print_count):
		report_type = ReportType()
		last_time = time.time() - TIME_MAX
		for t in range(self.nc.getTimestampLen()):
			current_time = time.time()
			if  t in [0, self.nc.getTimestampLen()-1] or current_time - last_time >= TIME_MAX:
				print('%s: %s, processed timestep %d of %d' % (util.get_current_time(), message, t+1, self.nc.getTimestampLen()))
				last_time = current_time
			timestamp = self.nc.getTimestamp(t)
			watermovervolume = 0.0 
			in_volume_total = 0.0
			out_volume_total = 0.0
			watermover_names = []
			watermover_names = sorted(watermovers.keys())
			for j in range(len(watermover_names)):
				watermover_name = watermover_names[j]
				in_volume = 0.0
				out_volume = 0.0
				volume = 0.0
			
				for k in watermovers[watermover_name]['in']:
					#if use_self.nc_utils:
					#	watermovervolume = self.nc_utils.get_watermover_volume(t, k)
					#else:
					watermovervolume = float(self.nc._watermovervolume[t][k])
					in_volume += watermovervolume
					in_volume_total += watermovervolume
					volume += watermovervolume
				for k in watermovers[watermover_name]['out']:
					#if use_nc_utils:
					#	watermovervolume = nc_utils.get_watermover_volume(t, k)
					#else:
					watermovervolume = float(self.nc._watermovervolume[t][k])
					out_volume += watermovervolume
					out_volume_total += watermovervolume
					volume -= watermovervolume
				if watermover_name == report_type.manning_circle and segment_watermovers:
					for segment_watermover in segment_watermovers:
						#if use_nc_utils:
						#	volume += nc_utils.get_watermover_volume(t, segment_watermover)
						#	else:
						volume += float(self.nc._watermovervolume[t][segment_watermover])
				(month, day, year) = [int(i) for i in timestamp.split()[0].split('/')]
		
				if year not in data['years']:
					data['years'][year] = {'all': [], 'values': {}, 'months': {}}
				if watermover_name not in data['years'][year]['values']:
					data['years'][year]['values'][watermover_name] = []
				data['years'][year]['all'].append(volume)
				data['years'][year]['values'][watermover_name].append(volume)
		
				if month not in data['years'][year]['months']:
					data['years'][year]['months'][month] = {'all': [], 'values': {}, 'days': {}}
				if watermover_name not in data['years'][year]['months'][month]['values']:
					data['years'][year]['months'][month]['values'][watermover_name] = []
				data['years'][year]['months'][month]['all'].append(volume)
				data['years'][year]['months'][month]['values'][watermover_name].append(volume)
		
				if day not in data['years'][year]['months'][month]['days']:
					data['years'][year]['months'][month]['days'][day] = {'all': [], 'values': {}}
				if watermover_name not in data['years'][year]['months'][month]['days'][day]['values']:
					data['years'][year]['months'][month]['days'][day]['values'][watermover_name] = []
				data['years'][year]['months'][month]['days'][day]['values'][watermover_name].append(volume)
				data['years'][year]['months'][month]['days'][day]['all'].append(volume)
		
				if month not in data['months']:
					data['months'][month] = {'all': [], 'values': {}}
				if watermover_name not in data['months'][month]['values']:
					data['months'][month]['values'][watermover_name] = []
				data['months'][month]['all'].append(volume)
				data['months'][month]['values'][watermover_name].append(volume)

				if 'seasonal' in data:
					for date_range in data['seasonal']['ranges']:
						range_year = ProcessData.get_range_years(date_range, month, day, year)
						if range_year not in data['seasonal']['values']['years']:
							data['seasonal']['values']['years'][range_year] = {}
						if date_range not in data['seasonal']['values']['years'][range_year]:
							data['seasonal']['values']['years'][range_year][date_range] = {'all': [], 'values': {}}
						if watermover_name not in data['seasonal']['values']['years'][range_year][date_range]['values']:
							data['seasonal']['values']['years'][range_year][date_range]['values'][watermover_name] = []
						if date_range not in data['seasonal']['values']['ranges']:
							data['seasonal']['values']['ranges'][date_range] = {'all': [], 'values': {}}
						if watermover_name not in data['seasonal']['values']['ranges'][date_range]['values']:
							data['seasonal']['values']['ranges'][date_range]['values'][watermover_name] = []
						if self.in_monthly_range(date_range, month, day):
							data['seasonal']['values']['years'][range_year][date_range]['values'][watermover_name].append(volume)
							data['seasonal']['values']['years'][range_year][date_range]['all'].append(volume)
							data['seasonal']['values']['ranges'][date_range]['values'][watermover_name].append(volume)
							data['seasonal']['values']['ranges'][date_range]['all'].append(volume)
				if j == 0:
					message1 = "%s,  %-15s,  %20.5f,  %20.5f,  %20.5f" % (timestamp, watermover_name, in_volume, out_volume, volume)
					outputfile.write(message1)
				else:
					outputfile.write('                   ,  %-15s,  %20.5f,  %20.5f,  %20.5f' % (watermover_name, in_volume, out_volume, volume))

	def main(self):
		print("Start")
		report_type = ReportType()
		seepage_report_table_w_segs = report_type.get_seepage_report_table_w_segs()
		print(seepage_report_table_w_segs)
		seasonal_data = list()
		if self.local_data.savedir:
			outdir = self.local_data.savedir
		elif self.local_data.savelabel:
			outdir = os.getcwd()
		else:
			outdir = "/tmp/%s_transect_%f" % (self.local_data.username, time.time())
		if os.path.exists(outdir) and not os.path.isdir(outdir):
			print('Error: the name you specified for output directory already exists and is not a directory' % outdir)
			sys.exit()
		if not os.path.exists(outdir):
			try:
				os.mkdir(outdir, 755)
			except OSError as e:
				print('mkdir OSError:' + e)
				sys.exit()
		print(self.nc.getStartDate())
		print('%s: Started loading netcdf' % (util.get_current_time()))
		if self.nc._watermovervolume == None:
			raise Exception('First netcdf file has no watermovervolumes')
		segments = list(self.local_data.segmentlist.keys())

		for i in range(len(segments)):
			if self.local_data.segmentlist[segments[i]]['waterbody'] in self.nc._watermovermap:
				self.local_data.segmentlist[segments[i]]['watermovers'] =  self.nc._watermovermap[segmentlist[segments[i]]['waterbody']]

		if self.local_data.segmentlist:
			current_seepage_report_table = seepage_report_table_w_segs
		else:
				current_seepage_report_table = report_type.get_seepage_report_table()
		if len(self.nc.coordinates.keys()) == 0:
			print("error No coordinates ")
		print('%s: finished loading netcdf' % (util.get_current_time()))
		print('%s: started finding watermovers' % (util.get_current_time()))
		for i in range(len(self.local_data.nodelist)):
			for j in range(len(self.local_data.nodelist[i]['node_pair'])):
				left = ProcessData.find_node_pair(self.local_data.nodelist[i]['node_pair'][j], self.nc._tricons_concat, self.nc._waterbodymap)
				right = ProcessData.find_node_pair(self.local_data.nodelist[i]['node_pair_reverse'][j], self.nc._tricons_concat,  self.nc._waterbodymap)
				if left != None and  right != None:
					watermover = (left, right)
					watermover_reverse = (right, left)
					if watermover in self.nc._watermovermap:
						for k in self.nc._watermovermap[watermover]:
							if self.nc._watermovertype[k] not in self.local_data.nodelist[i]['watermovers']:
								self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]] = {'in':[], 'out':[]}
							self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]]['in'].append(k)
							self.local_data.nodelist[i]['watermover_names'][self.nc._watermovername[k]] = 1
						self.local_data.nodelist[i]['watermover_in'] += self.nc._watermovermap[watermover]
					
					if watermover_reverse in self.nc._watermovermap:
						for k in self.nc._watermovermap[watermover_reverse]:
							if self.nc._watermovertype[k] not in self.local_data.nodelist[i]['watermovers']:
								self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]] = {'in':[], 'out':[]}
							self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]]['out'].append(k)
							self.local_data.nodelist[i]['watermover_names'][self.nc._watermovername[k]] = 1
						self.local_data.nodelist[i]['watermover_out'] += self.nc._watermovermap[watermover_reverse]
					adjacent_watermovers = self.get_adjacent_watermovers(watermover)
					D2S_left = D2S_right = D2S = None
					M2S_left = M2S_right = M2S = None
					for adjacent_watermover in adjacent_watermovers:
						for k in self.nc._watermovermap[adjacent_watermover]:
							if self.nc._watermovertype[k] == 'LevSeepMarshToSegMover':
								if adjacent_watermover[0] == left:
									M2S_left = k
								elif adjacent_watermover[0] == right:
									M2S_right = k
							elif self.nc._watermovertype[k] == 'LevSeepDryToSegMover':
								if adjacent_watermover[0] == left:
									D2S_left = k
								elif adjacent_watermover[0] == right:
									D2S_right = k
					if M2S_left and D2S_right:
						M2S = M2S_left
						D2S = D2S_right
					elif M2S_right and D2S_left:
						M2S = M2S_right
						D2S = D2S_left
					if D2S and M2S:
						if re.search("%s" % left, self.nc._watermovername[M2S]):
							if self.nc._watermovertype[M2S] not in self.local_data.nodelist[i]['watermovers']:
								self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[M2S]] = {'in':[], 'out':[]}
							self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[M2S]]['in'].append(M2S)
							self.local_data.nodelist[i]['watermover_names'][self.nc._watermovername[M2S]] = 1
						else: # re.search("%s" % right, nc._watermovername[M2S]):
							if self.nc._watermovertype[M2S] not in self.local_data.nodelist[i]['watermovers']:
								self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[M2S]] = {'in':[], 'out':[]}
							self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[M2S]]['out'].append(M2S)
							self.local_data.nodelist[i]['watermover_names'][self.nc._watermovername[M2S]] = 1
				elif left != None or right != None:
					if left in self.nc._external_cell_id_left:
						for k in self.nc._external_cell_id_left[left]:
							if self.nc._watermovertype[k] not in self.local_data.nodelist[i]['watermovers']:
								self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]] = {'in':[], 'out':[]}
							self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]]['in'].append(k)
							self.local_data.nodelist[i]['watermover_names'][self.nc._watermovername[k]] = 1
					elif right in self.nc._external_cell_id_right:
						for k in self.nc._external_cell_id_right[right]:
							if self.nc._watermovertype[k] not in self.local_data.nodelist[i]['watermovers']:
								self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]] = {'in':[], 'out':[]}
							self.local_data.nodelist[i]['watermovers'][self.nc._watermovertype[k]]['out'].append(k)
							self.local_data.nodelist[i]['watermover_names'][self.nc._watermovername[k]] = 1
		print(outdir)
		if self.local_data.savelabel:
			filename = '%s/%s_dailyinout.csv' % (outdir, self.local_data.savelabel)
			filename1 = '%s/%s_daily.csv' % (outdir, self.local_data.savelabel)
			filename2a = '%s/%s_monthly_averages.csv' % (outdir, self.local_data.savelabel)
			filename2b = '%s/%s_monthly_totals.csv' % (outdir, self.local_data.savelabel)
			filename2c = '%s/%s_average_month.csv' % (outdir, self.local_data.savelabel)
			filename3a = '%s/%s_yearly_averages.csv' % (outdir, self.local_data.savelabel)
			filename3b = '%s/%s_yearly_totals.csv' % (outdir, self.local_data.savelabel)
			filename4a = '%s/%s_season_averages.csv' % (outdir, self.local_data.savelabel)
			filename4b = '%s/%s_season_totals.csv' % (outdir, self.local_data.savelabel)
			filename5 = '%s/%s_seepage_transect.csv' % (outdir, self.local_data.savelabel)
		else:
			filename = '%s/transect_report_dailyinout.csv' % outdir
			filename1 = '%s/transect_report_daily.csv' % outdir
			filename2a = '%s/transect_report_monthly_averages.csv' % outdir
			filename2b = '%s/transect_report_monthly_totals.csv' % outdir
			filename2c = '%s/transect_report_average_month.csv' % outdir
			filename3a = '%s/transect_report_yearly_averages.csv' % outdir
			filename3b = '%s/transect_report_yearly_totals.csv' % outdir
			filename4a = '%s/transect_report_season_averages.csv' % outdir
			filename4b = '%s/transect_report_season_totals.csv' % outdir
			filename5 = '%s/transect_report_seepage_transect.csv' % outdir
		files = []
		print(self.local_data.report_type_list)
		if report_type.series_report in self.local_data.report_type_list:
			outputfile = open(filename, 'w')
			files.append(filename)
		else:
			outputfile = open('/dev/null', 'w')
		outputfile.write('Transect Report,')
		outputfile.write('RSM GUI: Transect Tool,')
		outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time())))
		data = {}
		last_time = None
		start_time = time.time()
		len_nodelist = len(self.local_data.nodelist)
		segment_watermovers = None
		print('%s: started processing nodes' % (util.get_current_time()))
		for i in range(len_nodelist):
			message = 'node %s of %s' % (i+1, len_nodelist)
			current_time = time.time()
			if last_time != None:
				delta_time = current_time-last_time
				projected_end_time = current_time + (delta_time * (len_nodelist-(i+1)))
				print("%s: %s, last node took %f seconds, projected finish: %s" % (util.get_current_time(current_time), message, delta_time, util.get_current_time(projected_end_time)))
			else:
				print("%s: %s" % (util.get_current_time(current_time), message))
			data[i] = {'nodelist': self.local_data.nodelist[i], 'months': {}, 'years': {}}
			if report_type.seasonal_average_report in self.local_data.report_type_list or \
				report_type.seasonal_totals_report in self.local_data.report_type_list:
				data[i]['seasonal'] = {'ranges': self.get_seasonal_data(seasonal_data), 'values': {'years':{}, 'ranges':{}}}
			outputfile.write('                               ')
			outputfile.write('_________________________________________________________')
			outputfile.write( 'The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']])))
			if len(self.nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(self.nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line = line + " "
					line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f' % (line, total_distance))
			line = ''	
			for nodepair in data[i]['nodelist']['node_pair']:
					line += ('(%s)' % ' '.join(['%d'%node for node in nodepair]))
			outputfile.write('Wall  [%s]' % line)
			watermover_names = sorted(data[i]['nodelist']['watermover_names'].keys())
			line = ''
			for watermover_name in watermover_names:
				line += '"%s" ' % watermover_name
			outputfile.write('Watermovers  [%s]' % line.strip())
			outputfile.write('Timeperiod: %s - %s,' %  (self.nc.getStartDate(), self.nc.getEndDate())) 
			outputfile.write('DATE               ,  TYPE           ,  %-20s,  %-20s,  %-20s' % ('IN VOL (%s)' % self.nc._watermovervolume_units, 'OUT VOL (%s)' % self.nc._watermovervolume_units, 'TOTAL VOL (%s)' % self.nc._watermovervolume_units))
			outputfile.write('----               ,  ----           ,  --------------------,  --------------------,  --------------------') 
			last_month = None
			last_year = None
			if True in [self.local_data.nodelist[i]['node_pair'][j] in self.local_data.segmentlist.keys() for j in range(len(nodelist[i]['node_pair']))]:
				segment_watermovers = []
				for j in range(len(self.local_data.nodelist[i]['node_pair'])):
					if self.local_data.nodelist[i]['node_pair'][j] in self.local_data.segmentlist.keys():
						for segment_watermover in self.local_data.segmentlist[self.local_data.nodelist[i]['node_pair'][j]]['watermovers']:
							segment_watermovers.append(segment_watermover)
				self.timestamp_loop(message, self.local_data.nodelist[i]['watermovers'], segment_watermovers, data[i], outputfile, print_count)
			else:
				self.timestamp_loop(message, self.local_data.nodelist[i]['watermovers'], None, data[i], outputfile, print_count)
			last_time = current_time
		outputfile.close()
		print('%s: finished processing nodes' % (util.get_current_time()))
		if report_type.daily_report in self.local_data.report_type_list:
			print('%s: generating daily report' % (util.get_current_time()))
			CSVOutput.print_daily_report(filename1, self.nc, data, self.local_data.seepage_report_list)
			files.append(filename1)
		if report_type.monthly_averages_report in self.local_data.report_type_list:
			print('%s: generating monthly averages report' % (util.get_current_time()))
			CSVOutput.print_monthly_averages_report(filename2a, self.nc, data, self.local_data.seepage_report_list)
			files.append(filename2a)
		if report_type.monthly_totals_report in report_type_button:
			print('%s: generating monthly totals report' % (util.get_current_time()))
			CSVOutput.print_monthly_totals_report(filename2b, self.nc, data, seepage_report_button)
			files.append(filename2b)
		if report_type.average_month_report in report_type_button:
			print('%s: generating average month report' % (util.get_current_time()))
			CSVOutput.print_average_month_report(filename2c, self.nc, data, seepage_report_button)
			files.append(filename2c)
		if report_type.yearly_averages_report in report_type_button:
			print('%s: generating yearly averages report' % (util.get_current_time()))
			CSVOutput.print_yearly_averages_report(filename3a, self.nc, data, seepage_report_button)
			files.append(filename3a)
		if report_type.yearly_totals_report in report_type_button:
			print('%s: generating yearly totals report' % (util.get_current_time()))
			CSVOutput.print_yearly_totals_report(filename3b, self.nc, data, seepage_report_button)
			files.append(filename3b)
		if report_type.seasonal_average_report in report_type_button:
			print('%s: generating seasonal average report' % (util.get_current_time()))
			CSVOutput.print_seasonal_average_report(filename4a, self.nc, data, seepage_report_button)
			files.append(filename4a)
		if report_type.seasonal_totals_report in report_type_button:
			print('%s: generating seasonal totals report' % (util.get_current_time()))
			CSVOutput.print_seasonal_totals_report(filename4b, self.nc, data, seepage_report_button)
			files.append(filename4b)
		end_time = time.time()
		print('%s: finished generating reports, total processing time %s' % (util.get_current_time(), util.get_total_time(end_time-start_time)))
		if not self.local_data.savedir:
			os.system('nedit %s; rm -rf %s' % ((' '.join(files)), outdir))
		else:
			print('%s: created %s' % (util.get_current_time(), ('\n%s: created '%util.get_current_time()).join(files)))
		del self.local_data
		self.files = files
		self.data = data



if __name__ == "__main__":
	if len(sys.argv) > 1:
		class PMG_IO:
			pass
		import argparse
		program_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
		usage_string = '''%s [wbbudget netCDF file] [mesh node ID file] -2nsatdmMyYolf

EXAMPLE: %s wbbudget.nc meshnodes.txt -l ALT5 -s -d''' % (program_name, program_name)
		description = '''The Transect Tool provides a means to calculate flows across a transect using 
			the wbbudgetpackage netCDF output file.  You must provide a <wbbudgetpackage> 
			netCDF file and an ascii file containing a list of mesh node IDs defining each
			transect. The list of node IDs must be on a single line separated by spaces.  
			The file can contain multiple lines, one for each transect.                   
			THE ORDER IN WHICH THE NODES ARE LISTED IS IMPORTANT.                         
			If you were standing on the transect looking from the first node to the second
			node, the upstream (source) will be on the left, and the downstream (sink)    
			will be on the right side of the transect. Output from this tool includes     
			daily, monthly, annual summary reports and an inflow outflow report. The      
			output will be written to the outdirectory and if none is defined, it will    
			be written to the current directory.'''

		parser = argparse.ArgumentParser(prog=program_name,\
			 formatter_class=argparse.RawDescriptionHelpFormatter,\
				  usage=usage_string, description=description)
		
		parser.add_argument('infile', nargs='?', type=argparse.FileType('r'))

		parser.add_argument('-j','--JSON',
			default='',
			help= "Switch Input to JSON.")
		parser.add_argument('-2', '--netcdf2',
			default="",
			action='store',
			help='2nd optional netCDF file if no meshNodeMap in 1st')
		parser.add_argument('-n', '--normal',
						action='store_true',
						default=True,
						help='Indicate normal report (default unless specified)')
		parser.add_argument('-s', '--seepage',
						action='store_true',
						default=False,
						help='Indicate seepage report')
		parser.add_argument('-a', '--all',
						action='store_true',
						default=False,
						help='Indicate that all report types should be output (default unless specified)')
		parser.add_argument('-T', '--Timing',
						action='store_true',
						default=False,
						help='Indicate that Timing Transect PMG  should be output')
		parser.add_argument('-D', '--Distribution',
						action='store_true',
						default=False,
						help='Indicate that Timing Transect PMG  should be output')
		parser.add_argument('-C', '--Continuity',
						action='store_true',
						default=False,
						help='Indicate that Timing Transect PMG  should be output')
		parser.add_argument('-t', '--time',
						action='store_true',
						default=False,
						help='Indicate that time series inflow outflow report type should be output')
		parser.add_argument('-d', '--daily',
						action='store_true',
						default=False,
						help='Indicate that daily report type should be output')
		parser.add_argument('-m', '--monthly',
						action='store_true',
						default=False,
						help='Indicate that monthly report type should be output')
		parser.add_argument('-M', '--monthly_average',
						action='store_true',
						default=False,
						help='Indicate that monthly average report type should be output')
		parser.add_argument('-y', '--yearly',
						action='store_true',
						default=False,
						help='Indicate that yearly report type should be output')
		parser.add_argument('-Y', '--yearly_average',
						action='store_true',
						default=False,
						help='Indicate that yearly average report type should be output')
		parser.add_argument('-o', '--outdirectory',
						action='store',
						default='',
						help="Directory to write output to.  If the directory doesn't exist, it will be created by the program. Defaults to current directory if not defined. ")
		parser.add_argument('-l', '--label',
						action='store',
						default='',
						help='This option forces the output files to have their file names preceded with the passed in label name.')
		parser.add_argument('-f', '--force',
						action='store_true',
						default=False,
						help='Force rewrite of existing files.  This flag is necessary if the output files already exists. NOTE: this attribute is no longer used.' 
							+'It is included only to be backwards compatable.')
		parser.parse_args(namespace = PMG_IO)
		
		if PMG_IO.infile:	
			report_type = ReportType()
			try:
				seepage_report_button = list()
				report_type_button = list()
				outdir = os.getcwd()
				if PMG_IO.seepage:
					 seepage_report_button.append(report_type.seepage_report)
				if PMG_IO.time:
					report_type_button.append(report_type.series_report)
				if PMG_IO.monthly:
					report_type_button.append(report_type.monthly_totals_report)
				if PMG_IO.daily:
					report_type_button.append(report_type.daily_report)
				if PMG_IO.monthly_average:
					report_type_button.append(report_type.monthly_averages_report)
				if PMG_IO.yearly:
					report_type_button.append(report_type.yearly_totals_report)
				if PMG_IO.yearly_average:
					report_type_button.append(report_type.yearly_averages_report)
				if PMG_IO.all:
					report_type_button = report_type.get_report_types()

				if PMG_IO.outdirectory:
					outdir = PMG_IO.outdirectory
				import gc
				input_type = "XML"
				continuity_distribution = "Continuity"
				username = getpass.getuser()
				pmg_data = PMG_Data.PMGMainData(PMG_IO.infile.name, input_type)
				for key, value in pmg_data.data.items():
					transect_data = value
					transect_group_data = dict()
					transect_group_data["name"] = transect_data.run_name
					c_outdir = outdir
					if PMG_IO.Timing:
						target = Transect_Timing_Process.read_csv_file(transect_data.target)
					if PMG_IO.Distribution:
						continuity_distribution = "Distribution"
					if PMG_IO.Continuity or PMG_IO.Distribution:
						target = Transect_Continuity_Process.read_csv_file(transect_data.target)
						target_run_data = dict()
						try:
							target_data_pd , parent_sub_transect_names , child_sub_transect_names = Transect_Continuity_Process.proccess_continuity_target(target,"TOTAL (ft^3)")
							target_run_data["data"] = target_data_pd
							target_run_data["parent_subt_names"] = parent_sub_transect_names
							transect_group_data["Target_data"] = target_run_data
							transect_group_data["COV_TYPE"] = continuity_distribution
						except:
							print("Please Review the Target")
					nodelist = ProcessData.get_nodelist(transect_data.nodes)
					segmentlist = dict()
					if transect_data.segments:
						segmentlist = ProcessData.get_segmentlist(transect_data.segments)
						print(segmentlist)
					alt_run_name = list()
					for netCDF_path in transect_data.run_paths_files:
						gc.collect()
						wbbudget_name = netCDF_path["name"]
						alt_run_name.append(wbbudget_name)
						print("Model Run : %s" % wbbudget_name)
						wbbudget_netcdf_path = netCDF_path["file_name"]
						label = transect_data.run_name + "_" + wbbudget_name
						local_data = LocalData(wbbudget_netcdf_path, nodelist,\
							 seepage_report_button, report_type_button, outdir, label, segmentlist)
						
						tool = TransectTool(local_data)
						c_outdir = local_data.savedir
						tool.main()
						if PMG_IO.Continuity or PMG_IO.Distribution:
							continuity_run_data= dict()
							print("Processing Continuity")
							list_data = Transect_Continuity_Process.process(tool.nc, tool.data)
							main_data_dic = dict()
							for data in list_data:
								data_pd  = Transect_Continuity_Process.proccess_continuity(data,'TOTAL (FT^3)')
			
								main_data_dic.update(data_pd)
							alt_data = Transect_Continuity_Process.build_alt_data_cov(main_data_dic, parent_sub_transect_names , child_sub_transect_names)
						
							continuity_run_data["runname"] = wbbudget_name
							deviation_sum, deviation_ave, record_count = Transect_Continuity_Process.calculate_sum_of_differences(target_data_pd, alt_data)
							print("%s deviation_sum : %d" % (wbbudget_name, deviation_sum))
							continuity_run_data["data"] = alt_data
							continuity_run_data["deviation_sum"]  = deviation_sum
							continuity_run_data["deviation_ave"]  = deviation_ave
							continuity_run_data["deviation_count"]  = record_count
							continuity_run_data["index_score"]  = COV_THRESHOLD - deviation_ave
							continuity_run_data["parent_subt_names"] = parent_sub_transect_names
							transect_group_data[wbbudget_name] = continuity_run_data
						if PMG_IO.Distribution:
							print("Processing Distribution")
						if PMG_IO.Timing:
							print("Timing")
							list_data = Transect_Timing_Process.process(tool.nc, tool.data)
							for data2 in list_data:
								#print(data2.nodes)
								deviation_data = Transect_Timing_Process.create_timing_data(target, data2)
								#print(deviation_data[1966])
								print_data, boxplot_data = Transect_Timing_Process.process_data_pdf_report(deviation_data)
								report_name = "%s/%s_report.txt" % (local_data.savedir, label)
								CSVOutput.print_timing_report(report_name, transect_data.run_name, wbbudget_name, print_data)
								plot_filename = '%s/%s_timing.pdf' % (local_data.savedir, label)
								plot_timing = PMG_Transect_Timing(wbbudget_name, transect_data.run_name, boxplot_data, plot_filename , label)
								plot_timing.plot_timing_boxplot()
						#forcing a patch on a memory leak from orginal Transect Tool
						for index in local_data.nodelist:
							for key in index['watermovers'].keys():
								index['watermovers'][key] = {'in':[], 'out':[]}

						del local_data
						del tool
					if PMG_IO.Continuity or PMG_IO.Distribution:
						print("Creating Continuity Reports")
						transect_group_data["runames"] = alt_run_name
						transect_group_data["outdir"] = c_outdir
						
						CSVOutput.continuity_report(transect_group_data)
						PMG_Transect_Continuity.graph_cov_for_all_runs(transect_group_data)
						PMG_Transect_Continuity.boxplot_COV(transect_group_data)
						PMG_Transect_Continuity.graph_cov_100(transect_group_data)


											
			except Exception as e:
				print("error" + str(e) + " " + traceback.format_exc())