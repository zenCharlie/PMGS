import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FormatStrFormatter
from matplotlib.font_manager import FontProperties
import numpy as np
import seaborn 
import pandas as pd
import calendar
import time
import datetime
from pandas.plotting import register_matplotlib_converters
from abc import ABCMeta
import getpass
from PMG_Exceptions import *
import re

class PMG_Graphics(metaclass=ABCMeta):
	def __init__(self, data, filename, plot_title, _seaborn_styles = "darkgird" ):
		self.plot_title = plot_title
		self.filename = filename
		self.data = data 
		self.seaborn_styles = _seaborn_styles

class PMG_Transect_Continuity:

	@staticmethod
	def boxplot_COV(run_data):
		output = run_data["outdir"]
		continuity_distribution = run_data["COV_TYPE"]
		transects_names = run_data["name"].split("_")
		alt_run_names = run_data["runames"]
		plot_name_box = "%s/%s_%s_cont_precent_dist_%s.pdf" % (output, transects_names[0], transects_names[1], continuity_distribution)
		title = "%s of Sheetflow for Transects %s and %s -Distribution of Coefficient of Variation" % (continuity_distribution, transects_names[0], transects_names[1])
		subtitle = "Based on Monthly North-South Flow in %s and %s (1965 - 2005)" % (transects_names[0], transects_names[1])
		polt_dict = dict()
		for an in alt_run_names:
					t_data = run_data[an]["data"]
					polt_dict[run_data[an]["runname"]] = t_data["COV"]
					#print(type(t_data["COV"]))
		
		with PdfPages(plot_name_box) as pdf:
			with seaborn.axes_style("whitegrid"):
				
				fig, ax = plt.subplots(figsize=(11.0, 8.5))
				plt.suptitle("%s \n %s" % (title, subtitle))
				labels, cov_list = [*zip(*polt_dict.items())]
				ax.boxplot(cov_list, autorange=True, showfliers=False, showcaps=False)
				ax.set_ylabel('Coefficient of Variation')
				ax.set_xlabel('Alternatives')
				ax.set_xticklabels(labels)
				plt.text(.9,-0.07, "For Planning Purpose Only \n run using Transect Tool", verticalalignment='bottom', horizontalalignment='left', transform=ax.transAxes,fontsize=6)
				bottom_text = "Note 1: Flow is assumed positive in the south direction and negative in the north direction \n Note 2: Months with a coefficient of variation greater than 3.0 are set to 3.0.."
				plt.text(.3,-0.07, bottom_text,
					verticalalignment='bottom', horizontalalignment='right',
					transform=ax.transAxes,
					color='black', fontsize=6)
				pdf.savefig()
				plt.close() 

	@staticmethod
	def graph_cov_for_all_runs(run_data):
		continuity_distribution = run_data["COV_TYPE"]
		t_names = run_data["name"].split("_")
		output = run_data["outdir"]
		plot_name = "%s/%s_%s_cont_runs_%s.pdf" % (output, t_names[0], t_names[1], continuity_distribution)
		alt_run_names = run_data["runames"]
		with PdfPages(plot_name) as pdf:
			labels = list()
			alt_means = list()
			for an in alt_run_names:
				t_data = run_data[an]
				labels.append(t_data["runname"])
				alt_means.append(t_data["deviation_ave"])
			x = np.arange(len(labels))  # the label locations
			width = 0.25  # the width of the bars
			title = '%s of Sheetflow for Transects %s and %s - Index Score' % (continuity_distribution, t_names[0], t_names[1])
			subtitle = 'Based on Monthly North-South Flow in  %s and  %s (1965 - 2005)' % (t_names[0], t_names[1])
			fig, ax = plt.subplots(figsize=(11.0, 8.5))
			ax.bar(labels, alt_means, label='Alternatives')
			plt.suptitle("%s \n %s" % (title, subtitle))
			# Add some text for labels, title and custom x-axis tick labels, etc.
			ax.set_ylabel('Index Score')
			ax.set_xticks(x)
			ax.set_xlabel('Alternatives')
			ax.set_xticklabels(labels)
			fig.tight_layout()
			plt.text(0.9, -0.08, "For Planning Purposes Only\n Script Used: Transect Tool. \n Filename: %s" % plot_name, fontsize=6)
			bottom_text = "Note: An index score of 100'%' represents 0 deviation. An index score of 0'%' represents a\n \t deviation of 3.0. Months with a coefficient of variation greater than 3.0 are set to 3.0. \n *Identifies the average deviation for that alternative"
			plt.text(.3,-0.07, bottom_text,
				verticalalignment='bottom', horizontalalignment='right',
				transform=ax.transAxes,
				color='black', fontsize=6)
			pdf.savefig()
			plt.close()

	@staticmethod
	def split_list_half(_list):
		out_list = list()
		length = len(_list)
		middle_index = length//2 
		out_list.insert(0, _list[:middle_index])
		out_list.insert(1, _list[middle_index:])
		return out_list
	
	@staticmethod
	def graph_cov_100(run_data):
		output = run_data["outdir"]
		target_data = run_data["Target_data"]
		continuity_distribution = run_data["COV_TYPE"]
		transects_names = run_data["name"].split("_")
		alt_run_names = run_data["runames"]
		for alt_name in alt_run_names:
			alt_data = run_data[alt_name]
			data = alt_data["data"]
			t_data = target_data["data"]
			main_dates = [ datetime.datetime.strptime(date, '%m-%d-%Y') for date in data["Date"].drop_duplicates()]
			main_years = [int(d.year) for d in main_dates ]
			set_years = set(main_years)
			main_xtics = [ "01-%d" % d for d in set_years]
			xtics_lists = PMG_Transect_Continuity.split_list_half(main_xtics)
			plot_name = "%s/%s_%s_cont_pos_%s_%s.pdf" % (output,transects_names[0], transects_names[1], continuity_distribution, alt_data["runname"])
			cov_100_List = data['COV*100']
			cov_100_lists = PMG_Transect_Continuity.split_list_half(cov_100_List)
			target_100_list = t_data['COV*100']
			target_100_lists = PMG_Transect_Continuity.split_list_half(target_100_list)
			#print(cov_100_lists[0])
			with PdfPages(plot_name) as pdf:
				with seaborn.axes_style("whitegrid"):
					title = '%s of Sheetflow  in %s for Transects %s and %s - Index Score' % (continuity_distribution, alt_data["runname"], transects_names[0], transects_names[1])
					subtitle = 'Based on Monthly North-South Flow in  %s and  %s (1965 - 2005)' % (transects_names[0], transects_names[1])
					fig, ax = plt.subplots(figsize=(11.0, 8.5))
					plt.suptitle(title + "\n" + subtitle)
					#plt.set_title(subtitle)
					plt.subplot(2,1,1)
					xtics_lists[1]
					x = np.arange(len(cov_100_lists[0]))
					locs, labels = plt.xticks([i*12 for i in range(len(xtics_lists[1]))],xtics_lists[1])
					for label in labels:
						label.set_rotation(0)
					
					plt.bar(x,cov_100_lists[0] , align='center', width=0.05, edgecolor='red',linestyle="--", color='none')
					plt.bar(x,target_100_list[0] , align='center', width=0.05, edgecolor='blue',linestyle="--", color='none')
					plt.ylabel('Coefficient of Variation * 100')
					
					plt.tick_params(axis='x', which='major', labelsize=5)
					plt.subplot(2,1,2)
					plt.bar(x,cov_100_lists[1] , align='center', width=0.05, edgecolor='red',linestyle="--", color='none')
					plt.bar(x,target_100_list[1] , align='center', width=0.05, edgecolor='blue',linestyle="--", color='none')
					locs, labels = plt.xticks([i*12 for i in range(len(xtics_lists[1]))],xtics_lists[1])
					for label in labels:
						label.set_rotation(0)
					plt.ylabel('Coefficient of Variation * 100')
					plt.tick_params(axis='x', which='major', labelsize=5)
					plt.xlabel('Year')
					plt.tight_layout()
					plt.text(.8,-0.14, "For Planning Purpose Only \n run using Transect Tool. \n Filename: %s" % plot_name, verticalalignment='bottom', horizontalalignment='left', transform=ax.transAxes,fontsize=6)
					bottom_text = "Note: An index score of 100'%' represents 0 deviation. An index score of 0'%' represents a\n \t deviation of 3.0. Months with a coefficient of variation greater than 3.0 are set to 3.0. \n *Identifies the average deviation for that alternative"
					plt.text(.25,-0.14, bottom_text,
						verticalalignment='bottom', horizontalalignment='right',
						transform=ax.transAxes,
						color='black', fontsize=6)
					pdf.savefig()
					plt.close()

class PMG_Transect_Timing(PMG_Graphics):
	def __init__(self, transect_name, run_name, data, filename, plot_title, _seaborn_styles = "whitegird"):
		self.run_name = run_name
		self.transect_name = transect_name
		super().__init__(data, filename, plot_title, _seaborn_styles=_seaborn_styles)

	def plot_timing_boxplot(self):
		plot_name = self.filename 
		water_year_months = [calendar.month_abbr[11], calendar.month_abbr[12], calendar.month_abbr[1],\
			calendar.month_abbr[2], calendar.month_abbr[3], calendar.month_abbr[4], calendar.month_abbr[5],\
				calendar.month_abbr[6], calendar.month_abbr[7], calendar.month_abbr[8], calendar.month_abbr[9], calendar.month_abbr[10]]
		with PdfPages(plot_name) as pdf:
			with seaborn.axes_style("whitegrid"):
				fig, ax = plt.subplots(figsize=(11.0, 8.5))
				start_year = 1965
				end_year = 2005
				title_part_1 = "Timing of Sheet Flow - Deviation of"
				title_part_2 = "From Target by Month"
				title = "%s %s %s" % (title_part_1, self.run_name, title_part_2)
				subtitle = "Transect %s / %d - %d " %(self.transect_name, start_year, end_year)
				plt.suptitle("%s \n %s" % (title, subtitle), fontsize=14, fontweight='bold')

				plt.ylim(-1, 1)
				df = pd.DataFrame(self.data)
				df.columns = water_year_months
				axes = df.boxplot(autorange=True, showfliers=False, showcaps=False)
				plt.text(10, -1.25, "For Planning Purpose Only \n run using Transect Tool", fontsize=6)
				bottom_text = "Note 1: The y-scale is set from -1.0 to +1.0 for ease of comparison with other graphs and because it is the maximum \n range if flow always occurs in the prevailing direction."
				plt.text(.6,-0.09, bottom_text,
					verticalalignment='bottom', horizontalalignment='right',
					transform=ax.transAxes,
					color='black', fontsize=6)
				pdf.savefig()
				plt.close()

	
class SloughVegetationPlotData(PMG_Graphics):
	def get_marker(self, index):
		if index == 0:
			marker = '^'
		elif index == 1:
			marker = 's'
		elif index == 2:
			marker = 'o'
		elif index == 3:
			marker = 'x'
		elif index == 4:
			marker = 'D'
		elif index == 5:
			marker = 'v'
		elif index == 6:
			marker = '>'
		elif index == 7:
			marker = '<'
		else:
			marker = 's'
		return marker

	def get_color(self, index):
		if index == 0:
			color = 'green'
		elif index == 1:
			color = 'blue'
		elif index == 2:
			color = 'black'
		elif index == 3:
			color = 'orange'
		elif index == 4:
			color = 'red'
		elif index == 5:
			color = '#FFFF00'
		elif index == 6:
			color = '#CC77FF' #fuscia
		elif index == 7:
			color = '#FF66DD' #pink
		elif index == 8:
			color = '#CC8811' #pumpkin_pie
		elif index == 9:
			color = 'cyan'
		else:
			color = '#657383' #slate gray		#disable random color generation use Slate Gray instead:[disabled tuple(rand(3))]
		return color


	def plot_pmg6_gf(self, season):
		# name_hold = ""
		xaxis_label = []
		x= []
		y = []
		with PdfPages(self.filename) as pdf:
			with axes_style(self.seaborn_styles):
				fig, ax = plt.subplots(figsize=(11.0, 8.5))
			
				keys = [value[0] for value in self.data['scenarios']]
				for i in range(-1, len(keys)):
					if i == -1:
						key = keys[0]
						y = self.data['scenarios'][0][1]	#y is the data values i.e. 41 values one per year
						if len(y) == 41: 			   #41 year is default
							xaxis_label = ['    20','     ','     10 ','','','   ','','5  ','','     ','     ','     ','      ','3  ','     ','     ','     ','   ','','       2  ','','     ','     ','     ','     ','     ','     3 ','     ','     ','     ','      ','','   5 ','     ','     ','    ','      10  ','     ','',' 20','']
						else:
							#xaxis_label = int(100/len(y))
							for j in range(1,len(y)):
								xaxis_label.append(j*xaxis_label)
								x = [j for j in range(len(y))]
								label = (" ")
								plt.plot(x, y, ls='-', linewidth=2.0, c='w', mfc='w', mec='w', label=label,alpha=0.5)
					else:
						if len(y) == 41: 			   #41 year is default
							xaxis_label = ['    20','    ','     10 ','','','   ','','5  ','','     ','     ','     ','      ','3  ','     ','     ','     ','   ','','       2  ','','     ','     ','     ','     ','     ','     3 ','     ','     ','     ','      ','','   5 ','     ','     ','    ','      10  ','     ','',' 20','']
						else:
							#xaxis_label = int(100/len(y))
							for j in range(1,len(y)):
								xaxis_label.append(j*xaxis_label)
								x = [j for j in range(len(y))]
								label = (" ")
								plt.plot(x, y, ls='-', linewidth=2.0, c='w', mfc='w', mec='w', label=label,alpha=0.5)
						key = keys[i]
						y = self.data['scenarios'][i][1]   #y is actual data points
					#	name_hold = run_name + " " + season + " " + key
						c = self.get_color(i)
						m = self.get_marker(i)
						x = [j for j in range(len(y))]
						key_data = key.split('_')
						if re.search('PMTARGET', key, re.I):
							label = "  %s"%('PMTARGET')
						else:
							#Below is for the legend
							label = "  %s"%(key[0:])
						plt.plot(x, y, ls='-', marker=m, linewidth=2.0, c=c, mfc=c, mec='k',
								label=label,alpha=0.5)
				locs, labels = plt.xticks([i for i in range(len(xaxis_label))],xaxis_label)
				
				for label in labels:
					label.set_rotation(0)
				#x = [j for j in range(len(y))]
				#plt.xlim(x[0]-0.5, x[-1]+0.5)   #Controls the left and right indent on the xaxis
				
				plt.title(self.plot_title)
				#subplots controls the position of plots on the chart and the size of the chart area
				plt.subplots_adjust(top=0.85, bottom=0.18, left=0.07, right=0.85)  #left must be <= right, bottom cannot be >= top
				xlabel_text = '''<--------------------------------------------------------------------|---------------------------------------------------------------------->
                    Below Average                                                       Above Average
                    (Dry)                                                                      (Wet)
                    Return Period (yrs)'''
				#DRYDOWN XLABEL TEXT IS DIFFERENT FROM WET FREQUENCY
				xlabel_text_drydown = '''<--------------------------------------------------------------------|---------------------------------------------------------------------->
                        Below Average                                                       Above Average
                        (Wet)                                                                      (Dry)
                        Return Period (yrs)'''
				if season == ' (Dry)':
					xlabel_combined = xlabel_text_drydown
					ax.set_xlabel(xlabel_combined)
					ax.set_ylabel('Continuous Drydown 0.7 ft (days)')	 #seasonal is cumulative ponding wet or dry
				elif season == ' (Wet)':
					xlabel_combined = xlabel_text
					ax.set_xlabel(xlabel_combined)
					ax.set_ylabel('Continuous Hydroperiod 0.0ft (days)')  #frequency is number of days of continuous ponding wet/dry
				else:
					xlabel_combined = xlabel_text
					ax.set_xlabel(xlabel_combined)
					ax.set_ylabel('Depth (ft)')						   #seasonal is cumulative ponding wet or dry
				ax.grid(True)
				font = FontProperties()
				font.set_family('monospace')
				#LEGEND LOCATION OPTIONS:
				# #best=0 ,upper right= 1,upper left=2,lower left=3,lower right=4,right=5,center left=6,center right=7,lower center=8,upper center=9,center=10 
				ax.legend(numpoints=2, markerscale=1, prop=font,loc = 0)	#loc = 0 make the legend position dynamic,numpoint and markerscale controls size of legend markers
				pdf.savefig()
				plt.close()

	def plot_pmg6(self):
		import datetime
		with PdfPages(self.filename) as pdf:
			for data_type in range(0,4):
				values = self.data[data_type]
				title = "%s%s at %s" % (self.plot_title, \
					self.plot_types_tuple[data_type], self.irzone_name )
				width = 0.90
				with axes_style(self.seaborn_styles):
					fig, ax = plt.subplots(figsize=(10, 8))
					ax.set_ylabel(self.ylabel)
					ax.set_title(title)
					ax.grid(True)
					if min(values) < 0:
						ax.set_ylim(-100, 100)
					else:
						ax.set_ylim(0, 100)
					ax.bar(self.run_names_list, values, width)
					pdf.savefig()
					plt.close()
			metadata_pdf = pdf.infodict()
			metadata_pdf['Title'] = "%s at %s" % (self.plot_title, self.irzone_name)
			metadata_pdf['Author'] = self.username 
			metadata_pdf['CreationDate'] = datetime.datetime.today()


	def __init__(self, plot_title, pgm_values_list, plot_types_tuple, \
		ylabel, irzone_name, run_names_list, filename, _seaborn_styles = "darkgrid" ):
		self.username = getpass.getuser()
		self.ylabel = ylabel
		self.irzone_name = irzone_name
		self.plot_types_tuple = plot_types_tuple
		self.run_names_list = run_names_list
		super(SloughVegetationPlotData, self).__init__(pgm_values_list, filename, plot_title, _seaborn_styles) 

if __name__ == '__main__':
	username = "charles"
	irzone_name = "IR1004"
	filename = "%s.pdf" % irzone_name
	data_list = []
	data = {'ECB19RR': 68, 'ALTN2': 78, 'ALTO': 75, 'ALTQ': 79}
	names = list(data.keys())
	values = list(data.values())
	for i in range(0,4):
		data_list.append(values)
	ylabel = 'Percentage of Target Achieved'
	plot_title = "Slough Vegetation Alternative Scores\nfor "
	plot_types_list = ("Annual Maximum Continuous Hydroperiods","Annual Maximum Continuous Drydowns to 0.7\"","Wet Season Depths","Dry Season Depths")
	plot = SloughVegetationPlotData(plot_title, data_list, plot_types_list,
		ylabel, irzone_name, names, filename)
	plot.plot_pmg6()

