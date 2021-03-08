import time
import numpy as np
import math
from dataclasses import dataclass
from datetime import datetime

CANAL_MINIMUM = 300000
CANAL_MAXIMUM = 399999
TIME_MAX = 5
print_count = 100
COLUMN_WIDTH = 20
DECIMAL_PLACES = 5
SECS_PER_DAY = 86400.0
TIME_MAX = 5

@dataclass
class ReportType:
	seepage_report: str = 'Seepage Transect Report Format'
	series_report: str = 'Time Series Inflow/Outflow Report'
	daily_report: str = 'Daily Report'
	seasonal_average_report: str = 'Seasonal Average Report'
	seasonal_totals_report: str = 'Seasonal Totals Report'
	average_month_report: str = 'Average Month Report'
	monthly_averages_report: str = 'Monthly Averages Report'
	monthly_totals_report: str = 'Monthly Totals Report'
	yearly_averages_report: str = 'Yearly Averages Report'
	yearly_totals_report: str = 'Yearly Totals Report'
	darcy_circle: str = 'DarcyCircle'
	manning_circle: str = 'ManningCircle'
	marsh_to_dry: str = 'LevSeepMarshToDryMover'
	marsh_to_seg: str = 'LevSeepMarshToSegMover'
	dry_to_seg: str = 'LevSeepDryToSegMover'

	def get_seepage_report_table(self):
		seepage_report_table = dict([(watermover, watermover) for watermover in self.get_seepage_report_fields()])
		return seepage_report_table
	
	def get_seepage_report_table_w_segs(self):
		seepage_report_table_w_segs = dict([(watermover, watermover) for watermover in self.get_seepage_report_fields()])
		seepage_report_table_w_segs[self.manning_circle] += '+Segment'
		return seepage_report_table_w_segs

	def get_seepage_report_fields(self):
		seepage_report_fields = [self.darcy_circle, self.manning_circle, self.marsh_to_dry, self.marsh_to_seg, self.dry_to_seg]
		return seepage_report_fields

	def get_report_types(self):
		report_types = [self.series_report, self.daily_report, self.seasonal_average_report,
			 self.seasonal_totals_report, self.average_month_report, self.monthly_averages_report, 
			 self.monthly_totals_report, self.yearly_averages_report, self.yearly_totals_report]
		return report_types

class ProcessData:
	@staticmethod
	def node_match(node, tricon):
		for i in range(len(tricon)-1):
			if node[0] == int(tricon[i]) and node[1] == int(tricon[i+1]):
				return 1
		return 0

	@staticmethod
	def intSort(a, b):
		if int(a) > int(b):
			return 1
		elif int(b) > int(a):
			return -1
		else:
			return 0

	@staticmethod
	def find_node_pair(node, tricons, waterbodymap):
		for i in range(len(tricons)):
			if ProcessData.node_match(node, tricons[i]):
				return int(waterbodymap[i])
		return None

	@staticmethod
	def get_range_years(year, date_range):
		(month1, day1, month2, day2) = date_range
		if month1 > month2 or (month1 == month2 and day1 > day2):
			return('%4d/%02d/%02d-%4d/%02d/%02d' % (year-1, month1, day1, year, month2, day2))
		else:
			return('%4d/%02d/%02d-%4d/%02d/%02d' % (year, month1, day1, year, month2, day2))

	@staticmethod
	def get_distance( nc, node_pair):
		n1, n2 = node_pair
		if ProcessData.find_node_pair(node_pair, nc._tricons_concat, nc._waterbodymap) \
			and ProcessData.find_node_pair([node_pair[1], node_pair[0]], nc._tricons_concat, nc._waterbodymap)\
			and ( n1 in nc.coordinates and n2 in nc.coordinates):
			x1, y1 = nc.coordinates[n1]
			x2, y2 = nc.coordinates[n2]
			distance = math.sqrt((x2-x1)*(x2-x1)+(y2-y1)*(y2-y1))
			return distance
		else:
			return 0

	@staticmethod
	def cmp_to_key(mycmp):
		'Convert a cmp= function into a key= function'
		class K:
			def __init__(self, obj, *args):
				self.obj = obj
			def __lt__(self, other):
				return mycmp(self.obj, other.obj) < 0
			def __gt__(self, other):
				return mycmp(self.obj, other.obj) > 0
			def __eq__(self, other):
				return mycmp(self.obj, other.obj) == 0
			def __le__(self, other):
				return mycmp(self.obj, other.obj) <= 0
			def __ge__(self, other):
				return mycmp(self.obj, other.obj) >= 0
			def __ne__(self, other):
				return mycmp(self.obj, other.obj) != 0
		return K

	@staticmethod
	def get_nodelist(nodes_list):
		nodelist = []
		for nodes in nodes_list:
			
			node = []
			wall = []
			node_pair = []
			node_pair_reverse = []
			for i in range(len(nodes)):
				node.append(int(nodes[i]))
				# set the data index to zero based by subtracting one
				wall.append(int(nodes[i]) - 1)
				if i > 0:
					node_pair.append((wall[i-1], wall[i]))
					node_pair_reverse.append((wall[i], wall[i-1]))
			nodelist.append({'node':node, 'wall':wall, 'node_pair':node_pair, 'node_pair_reverse':node_pair_reverse, \
						'watermover_names':{}, 'watermovers':{}, 'watermover_in':[], 'watermover_out':[]})
		return nodelist

	@staticmethod
	def get_segmentlist(segment_list) -> dict:
		segmentlist = {}
		for segment in segment_list:
			data = [value.strip() for value in segment.split(', \n')]
			# disregard anything but digits in the values so that things
			# like parenthesis don't affect converting to integer
			segment_watermover = [int(''.join([digit for digit in \
				value.strip() if digit.isdigit()])) for value in data[0].split()]
			node_pair = [int(''.join([digit for digit in value.strip() if digit.isdigit()])) for value in data[1].split()]
			segmentlist[(node_pair[0]-1, node_pair[1]-1)] = {'waterbody':(segment_watermover[0], segment_watermover[1])}
		return segmentlist

	@staticmethod
	def rangeSort(a, b):
		(month1a, day1a, month2a, day2a) = a
		(month1b, day1b, month2b, day2b) = b
		if month2a > month2b:
			return 1
		elif month2b > month2a:
			return -1
		else:
			return 0



class CSVOutput:

	@staticmethod
	def create_report_output(run_data, t_names):
		data = run_data["data"]
		parent_subt_names  = run_data["parent_subt_names"]
		temp_list = list(data .columns.values)
		header_target = [i for i in temp_list if i not in parent_subt_names]
		header_target.insert(1, t_names[0])
		header_target.insert(2, t_names[1])
		output = data.to_csv(None, '\t', header=header_target,index=False)
		return output

	@staticmethod
	def continuity_report(transect_group_data):
		continuity_distribution = transect_group_data["COV_TYPE"]
		alt_run_names = transect_group_data["runames"]
		output = transect_group_data["outdir"]
		target_run_data = transect_group_data["Target_data"] 
		transects_names = transect_group_data["name"].split("_")
		subtitle = "Based on Monthly North-South Flow in %s and %s (1965 - 2005)" % (transects_names[0],transects_names[1])
		main_title = "%s of Sheetflow for Transects %s and %s - Distribution of Coefficient of Variation" %  (continuity_distribution, transects_names[0],transects_names[1])
		target_output = CSVOutput.create_report_output(target_run_data, transects_names)
		report_name = "%s/%s_%s_%s.txt" % (output, transects_names[0],transects_names[1], continuity_distribution)
		with open(report_name, "w") as outputfile:
			now = datetime.now()
			outputfile.write(main_title)
			outputfile.write('\n')
			outputfile.write(subtitle)
			outputfile.write('\n')
			outputfile.write("Date: %s \n" % now.strftime("%d/%m/%Y %H:%M:%S"))
			outputfile.write('\n')
			outputfile.write("REPORT FOR: Target \n")
			outputfile.write(target_output)
			outputfile.write('\n')
			for alt_name in alt_run_names:
				alt_run_data = transect_group_data[alt_name]
				alt_output = CSVOutput.create_report_output(alt_run_data, transects_names)
				outputfile.write('\n')
				outputfile.write("REPORT FOR: %s\n" % alt_run_data["runname"] )
				outputfile.write(alt_output)
				outputfile.write('\n')
				outputfile.write('Sum of Deviations(%s): %.13f' % (alt_run_data["runname"], alt_run_data["deviation_sum"]))
				outputfile.write('\n')
				outputfile.write('Average Deviation(%s): %.13f' % (alt_run_data["runname"], alt_run_data["deviation_ave"]))
				outputfile.write('\n')
				outputfile.write('Number of Deviations(%s): %.13f' % (alt_run_data["runname"], alt_run_data["deviation_count"]))
				outputfile.write('\n')
				outputfile.write('Index Score (%s): %.13f' % (alt_run_data["runname"], alt_run_data["index_score"]))

	@staticmethod
	def print_yearly_averages_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		outputfile = open(filename, 'w')
		outputfile.write('Yearly Averages Transect Report, \n') 
		outputfile.write('RSM GUI: Transect Tool, \n') 
		outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time()))) 
		for i in range(len(data)):
			outputfile.write('                               \n') 
			outputfile.write('_________________________________________________________ \n')
			outputfile.write('The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']]))) 
			if len(nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line = line + " "
					line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f\n' % (line, total_distance)) 
			line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
			outputfile.write('Wall  [%s]' % line) 
			line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
			outputfile.write('Watermovers  [%s]\n' % line.strip()) 
			outputfile.write('Timeperiod: %s - %s,' %  (nc. getStartDate(), nc.getEndDate())) 
			outputfile.write('DATE, ') 
			if report_type.seepage_report in seepage_report_button:
				watermovers = report_type.get_seepage_report_fields()
			else:
				watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
			local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
			for watermover in watermovers:
				outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover]))
			outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units) 
			outputfile.write('----, ')
			for watermover in watermovers:
				outputfile.write(('-'*max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])))+', ')
			outputfile.write('--------------------\n')
			for year in sorted(data[i]['years'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
				outputfile.write('%d, '%(year)) 
				for watermover in watermovers:
					if watermover in data[i]['years'][year]['values']:
						outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES,  np.mean(data[i]['years'][year]['values'][watermover])))
					else:
						outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover]))))
				outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.mean(data[i]['years'][year]['all']))) 
		outputfile.close()

	@staticmethod
	def print_seasonal_totals_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		outputfile = open(filename, 'w')
		outputfile.write('Seasonal Totals Transect Report, \n') 
		outputfile.write('RSM GUI: Transect Tool, \n') 
		outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time()))) 
		for i in range(len(data)):
			outputfile.write('                               \n') 
			outputfile.write('_________________________________________________________ \n')
			outputfile.write('The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']]))) 
			if len(nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line = line + " "
					line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f\n' % (line, total_distance)) 
			line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
			outputfile.write('Wall  [%s]' % line) 
			line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
			outputfile.write('Watermovers  [%s]\n' % line.strip()) 
			outputfile.write('Timeperiod: %s - %s,' %  (nc. getStartDate(), nc.getEndDate())) 
			outputfile.write('SEASON DATES         , ') 
			if report_type.seepage_report in seepage_report_button:
				watermovers = report_type.get_seepage_report_fields()
			else:
				watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
			local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
			for watermover in watermovers:
				outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover]))
			outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units) 
			outputfile.write('---------------------, ')
			for watermover in watermovers:
				outputfile.write(('-'*max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])))+', ')
			outputfile.write('--------------------\n')
			for year in sorted(data[i]['seasonal']['values']['years'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
				for date_range in sorted(data[i]['seasonal']['values']['years'][year].keys(), ProcessData.rangeSort):
					outputfile.write( '%s, ' % ProcessData.get_range_years(year, date_range))
					for watermover in watermovers:
						if watermover in data[i]['seasonal']['values']['years'][year][date_range]['values']:
							outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES, np.sum(data[i]['seasonal']['values']['years'][year][date_range]['values'][watermover]))) 
						else:
							outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])))) 
					outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.sum(data[i]['seasonal']['values']['years'][year][date_range]['all']))) 
		outputfile.close()

	@staticmethod
	def print_monthly_averages_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		print("test")
		with open(filename, 'w') as outputfile:
			outputfile.write('Monthly Averages Transect Report, \n')
			outputfile.write('RSM GUI: Transect Tool, \n') 
			outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time())))
			for i in range(len(data)):
				outputfile.write('                               ')
				outputfile.write('_________________________________________________________ \n')
				outputfile.write('The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']]))) 
				if len(nc.coordinates.keys()) != 0:
					total_distance = 0
					line = ''
					for nodepair in data[i]['nodelist']['node_pair']:
						distance = ProcessData.get_distance(nc, nodepair)
						total_distance = total_distance + distance
						if line:
							line = line + " "
						line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
					outputfile.write('%s Transect=%.0f\n' % (line, total_distance)) 
				line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
				outputfile.write('Wall  [%s]' % line)
				print("working")
				line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
				outputfile.write('Watermovers  [%s]\n' % line.strip())
				outputfile.write('Timeperiod: %s - %s,' %  (nc. getStartDate(), nc.getEndDate())) 
				outputfile.write('DATE   , ')
				if report_type.seepage_report in seepage_report_button:
					watermovers = report_type.get_seepage_report_fields()
				else:
					watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
				local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
				for watermover in watermovers:
					outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover]))
				outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units)
				outputfile.write('-------, \n')
				for watermover in watermovers:
					outputfile.write(('-'*max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])))+', ')
				outputfile.write('--------------------\n')
				for year in sorted(data[i]['years'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
					for month in sorted(data[i]['years'][year]['months'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
						outputfile.write('%02d/%d, '%(month, year))
						for watermover in watermovers:
							if watermover in data[i]['years'][year]['months'][month]['values']:
								outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES, np.mean(data[i]['years'][year]['months'][month]['values'][watermover])))
							else:
								outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover]))))
						outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.sum(data[i]['years'][year]['months'][month]['all']))) 
		outputfile.close()

	@staticmethod
	def print_seasonal_average_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		outputfile = open(filename, 'w')
		outputfile.write('Average Season Transect Report, \n') 
		outputfile.write('RSM GUI: Transect Tool, \n') 
		outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time()))) 
		for i in range(len(data)):
			outputfile.write('                               \n') 
			outputfile.write('_________________________________________________________ \n')
			outputfile.write('The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']]))) 
			if len(nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line = line + " "
					line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f\n' % (line, total_distance)) 
			line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
			outputfile.write('Wall  [%s]' % line) 
			line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
			outputfile.write('Watermovers  [%s]\n' % line.strip()) 
			outputfile.write('Timeperiod: %s - %s,' %  (nc. getStartDate(), nc.getEndDate())) 
			outputfile.write('SEASON DATES, ') 
			if report_type.seepage_report in seepage_report_button:
				watermovers = report_type.get_seepage_report_fields()
			else:
				watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
			local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
			for watermover in watermovers:
				outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover])) 
			outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units) 
			outputfile.write('------------, ')
			for watermover in watermovers:
				outputfile.write(('-'*max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])))+', ') 
			outputfile.write('--------------------\n')
			for date_range in sorted(data[i]['seasonal']['values']['ranges'].keys(), ProcessData.rangeSort):
				outputfile.write(' %s, ' % ProcessData.get_range(date_range)) 
				for watermover in watermovers:
					if watermover in data[i]['seasonal']['values']['ranges'][date_range]['values']:
						outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES,  np.mean(data[i]['seasonal']['values']['ranges'][date_range]['values'][watermover]))) 
					else:
						outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])))) 
				outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.mean(data[i]['seasonal']['values']['ranges'][date_range]['all']))) 
		outputfile.close()

	@staticmethod
	def print_yearly_totals_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		outputfile = open(filename, 'w')
		outputfile.write('Yearly Totals Transect Report, \n') 
		outputfile.write('RSM GUI: Transect Tool, \n') 
		outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time()))) 
		for i in range(len(data)):
			outputfile.write('                               \n') 
			outputfile.write('_________________________________________________________ \n')
			outputfile.write('The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']]))) 
			if len(nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line = line + " "
					line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f\n' % (line, total_distance)) 
			line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
			outputfile.write('Wall  [%s]' % line) 
			line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
			outputfile.write('Watermovers  [%s]\n' % line.strip()) 
			outputfile.write('Timeperiod: %s - %s,' %  (nc. getStartDate(), nc.getEndDate())) 
			outputfile.write('DATE, ')
			if report_type.seepage_report in seepage_report_button:
				watermovers = report_type.get_seepage_report_fields()
			else:
				watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
			local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
			for watermover in watermovers:
				outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover]))
			outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units) 
			outputfile.write('----, ')
			for watermover in watermovers:
				outputfile.write(('-'*max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])))+', ') 
			outputfile.write('--------------------\n')
			for year in sorted(data[i]['years'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
				outputfile.write('%d, '%(year))
				for watermover in watermovers:
					if watermover in data[i]['years'][year]['values']:
						outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES,  sum(data[i]['years'][year]['values'][watermover])))
					else:
						outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])))) 
				outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.sum(data[i]['years'][year]['all']))) 
		outputfile.close()
		
	@staticmethod
	def print_average_month_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		outputfile = open(filename, 'w')
		outputfile.write('Average Month Transect Report, \n') 
		outputfile.write('RSM GUI: Transect Tool, \n') 
		outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time()))) 
		for i in range(len(data)):
			outputfile.write('                               \n') 
			outputfile.write('_________________________________________________________ \n')
			outputfile.write('The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']]))) 
			if len(nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line = line + " "
					line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f\n' % (line, total_distance)) 
			line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
			outputfile.write('Wall  [%s]' % line) 
			line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
			outputfile.write('Watermovers  [%s]\n' % line.strip()) 
			outputfile.write('Timeperiod: %s - %s,' %  (nc. getStartDate(), nc.getEndDate())) 
			outputfile.write('MONTH, ') 
			if report_type.seepage_report in seepage_report_button:
				watermovers = report_type.get_seepage_report_fields()
			else:
				watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
			local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
			for watermover in watermovers:
				outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover]))
			outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units) 
			outputfile.write('-----, ')
			for watermover in watermovers:
				outputfile.write(('-'*max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])))+', ')
			outputfile.write( '--------------------')
			for month in sorted(data[i]['months'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
				outputfile.write('   %02d, '%month)
				for watermover in watermovers:
					if watermover in data[i]['months'][month]['values']:
						outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES,  np.mean(data[i]['months'][month]['values'][watermover]))) 
					else:
						outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover]))))
				outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.mean(data[i]['months'][month]['all']))) 
		outputfile.close()

	@staticmethod
	def print_daily_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		outputfile = open(filename, 'w')
		outputfile.write('Daily Transect Report, \n')
		outputfile.write('RSM GUI: Transect Tool, \n')
		outputfile.write(time.strftime("%m/%d/%Y,", time.localtime(time.time())))
		for i in range(len(data)):
			outputfile.write('                               ')
			outputfile.write('_________________________________________________________')
			outputfile.write('The list of nodes is = [%s]' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']])))
			if len(nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line += " "
					line += "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f\n' % (line, total_distance))
			line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
			outputfile.write('Wall  [%s]' % line )
			line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
			outputfile.write('Watermovers  [%s]\n' % line )
			outputfile.write( 'Timeperiod: %s - %s,' %  (nc. getStartDate(), nc.getEndDate()))
			outputfile.write('DATE      , ')
			if report_type.seepage_report in seepage_report_button:
				watermovers = report_type.get_seepage_report_fields()
			else:
				watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
			local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
			for watermover in watermovers:
				outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover]))
			outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units)
			outputfile.write('----------, ')
			for watermover in watermovers:
				outputfile.write('%s, ' % ('-'*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover]))))
			outputfile.write('--------------------')
			for year in sorted(data[i]['years'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
				for month in sorted(data[i]['years'][year]['months'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
					for day in sorted(data[i]['years'][year]['months'][month]['days'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
						outputfile.write('%02d/%02d/%d, '%(month, day, year))
						for watermover in watermovers:
							if watermover in data[i]['years'][year]['months'][month]['days'][day]['values']:
								outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES,  sum(data[i]['years'][year]['months'][month]['days'][day]['values'][watermover])))
							else:
								outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover]))))
						outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.sum(data[i]['years'][year]['months'][month]['days'][day]['all']))) 
		outputfile.close()
	
	@staticmethod
	def print_monthly_totals_report(filename, nc, data, seepage_report_button):
		report_type = ReportType()
		current_seepage_report_table = report_type.get_seepage_report_table()
		outputfile = open(filename, 'w')
		outputfile.write('Monthly Totals Transect Report,\n')
		outputfile.write('RSM GUI: Transect Tool,\n')
		outputfile.write(time.strftime("%m/%d/%Y,\n", time.localtime(time.time())))
		for i in range(len(data)):
			outputfile.write('                               \n')
			outputfile.write('_________________________________________________________\n')
			outputfile.write('The list of nodes is = [%s] \n' % (' '.join(['%i'%node for node in data[i]['nodelist']['node']])))
			if len(nc.coordinates.keys()) != 0:
				total_distance = 0
				line = ''
				for nodepair in data[i]['nodelist']['node_pair']:
					distance = ProcessData.get_distance(nc, nodepair)
					total_distance = total_distance + distance
					if line:
						line = line + " "
					line = line + "Distance(%s %s)=%.0f," % (nodepair[0]+1, nodepair[1]+1, distance)
				outputfile.write('%s Transect=%.0f\n' % (line, total_distance))
			line = ''.join(['(%s)' % (' '.join(['%d' % node for node in nodepair])) for nodepair in data[i]['nodelist']['node_pair']])
			outputfile.write('Wall  [%s]\n' % line)
			line = ' '.join([watermover_name for watermover_name in sorted(data[i]['nodelist']['watermover_names'].keys())])
			outputfile.write('Watermovers  [%s]\n' % line.strip())
			outputfile.write('Timeperiod: %s - %s,\n' %  (nc.getStartDate(), nc.getEndDate()))
			outputfile.write('DATE   , ')

			if report_type.seepage_report in seepage_report_button:
				watermovers = report_type.get_seepage_report_fields()
			else:
				watermovers = sorted(data[i]['nodelist']['watermovers'].keys())
			local_seepage_report_table = dict([(watermover, current_seepage_report_table[watermover]+' (%s)' % nc._watermovervolume_units) for watermover in current_seepage_report_table.keys()])
			for watermover in watermovers:
				outputfile.write('%-*s, ' % (max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])), local_seepage_report_table[watermover]))
			outputfile.write('TOTAL (%s)\n' % nc._watermovervolume_units)
			outputfile.write('-------, \n')
			for watermover in watermovers:
				outputfile.write(('-'*max(COLUMN_WIDTH,len(local_seepage_report_table[watermover])))+', ')
			outputfile.write('--------------------')
			for year in sorted(data[i]['years'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
				for month in sorted(data[i]['years'][year]['months'].keys(), key=ProcessData.cmp_to_key(ProcessData.intSort)):
					outputfile.write('\n%02d/%d, '%(month, year))
					for watermover in watermovers:
						if watermover in data[i]['years'][year]['months'][month]['values']:
							outputfile.write('%*.*f, ' % (max(COLUMN_WIDTH, len(local_seepage_report_table[watermover])), DECIMAL_PLACES, sum(data[i]['years'][year]['months'][month]['values'][watermover])))
						else:
							outputfile.write('%s, ' % (' '*max(COLUMN_WIDTH, len(local_seepage_report_table[watermover]))))
					outputfile.write('%*.*f' % (COLUMN_WIDTH, DECIMAL_PLACES, np.sum(data[i]['years'][year]['months'][month]['all'])))
		outputfile.close()

	@staticmethod	
	def print_timing_report(report_name, transect_name, run_name, print_data):
		from datetime import datetime
		with open(report_name, "w") as outputfile:
			now = datetime.now()
			outputfile.write("Report: %s \n" % report_name)
			outputfile.write("Transect: %s \n" % transect_name)
			outputfile.write("Run: %s \n" % run_name)
			outputfile.write("Date: %s \n" % now.strftime("%d/%m/%Y %H:%M:%S"))
			outputfile.write("\n\n")
			outputfile.write("\n\n")
			title = "Timing Deviation from Target Monthly Discharge as Percentage of Annual Discharge"
			outputfile.write("Transect %s %s" % (transect_name, title))
			outputfile.write("\n\n")
			widths = [max(len(data[i]) for data in print_data) for i in range(len(print_data[0]))]
			for row in print_data:
				outputfile.write(' '.join(cell.ljust(width) for cell, width in zip(row, widths)))
				outputfile.write('\n')