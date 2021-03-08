import datetime

class PMGErrorMessage(Exception):
	def __init__(self, error_message, traceback_info):
		self.error_message = error_message
		self.traceback_info = "\n\n Error was raised, Details are: \n" + traceback_info
	def __str__(self):
		return (repr(self.error_message))

class EmpiricalFrequencyErrorMessage(PMGErrorMessage):
	def __init__(self, error_message, traceback_info):
		super(EmpiricalFrequencyErrorMessage, self).__init__(error_message, traceback_info)

class PMG6ErrorMessage(PMGErrorMessage):
	def __init__(self, error_message, traceback_info):
		super(PMG6ErrorMessage, self).__init__(error_message, traceback_info)

class PMGUtilitiesErrorMessage(PMGErrorMessage):
	def __init__(self, error_message, traceback_info):
		super(PMGUtilitiesErrorMessage, self).__init__(error_message, traceback_info)
		
class NetCDFErrorMessage(PMGErrorMessage):
	def __init__(self, error_message, traceback_info, file_name):
		self.file_name = file_name
		self.netcdf_message = "%s with the folllow file %s at line : \n %s " % (error_message, file_name, traceback_info)
		super(NetCDFErrorMessage, self).__init__(error_message, traceback_info)

class InputErrorMessage(PMGErrorMessage):
	def __switch_error_message(self, error_message):
		types = {
			"log_folder":"Error log_folder missing",
			"title":"Error title missing",
			"pmg_type":"Error pmg_type missing"
		}
		build_input_data = types.get(error_message,lambda: "Invalid Attribute")
		return build_input_data

	def __init__(self, error_message, traceback_info, file_name):
		error_message  = self.__switch_error_message(error_message)
		super(InputErrorMessage, self).__init__(error_message, traceback_info)
		self.file_name = file_name

class OutputErrorMessage(PMGErrorMessage):
	def __switch_error_message(self, error_message):
		types = {
			"folder":"Error output folder missing",
			"file":"Error writing outfile"
		}
		build_input_data = types.get(error_message,lambda: "Invalid Attribute")
		return build_input_data

	def __init__(self, error_message, traceback_info, folder_file_name):
		self.error_message  = self.__switch_error_message(error_message)
		super(OutputErrorMessage, self).__init__(error_message, traceback_info)
		self.file_name = folder_file_name

class SingletonErrorMessage(PMGErrorMessage):
	def __init__(self, error_message, traceback_info, interaction):
		error_message = ""
		if "set" in interaction.lower():
			error_message = "This has not been Instantiated. Please Implement correctly."
		if "get" in interaction.lower():
			error_message = "This has already been Instantiated. Please review your Implemention."
		super(SingletonErrorMessage, self).__init__(error_message, traceback_info)

class GraphicsErrorMessage(PMGErrorMessage):
	def __switch_error_message(self, error_message):
		types = {
			"data":"Error data missing",
			"title":"Error title missing",
			"plotting":"Issues ploting",
			"pmg_type":"Error pmg_type missing"
		}
		plotting_error = types.get(error_message,lambda: "Invalid Attribute")
		return plotting_error
	def __init__(self, error_message, traceback_info, file_name):
		error_message  = self.__switch_error_message(error_message)
		super(GraphicsErrorMessage, self).__init__(error_message, traceback_info)
		self.file_name = file_name

class LoggingErrorMessage(PMGErrorMessage):
	def __init__(self, error_message, traceback_info, file_name):
		super(LoggingErrorMessage, self).__init__(error_message, traceback_info)
		self.file_name = file_name
		self.error_message = "%s file %s" % (self.error_message, self.file_name)

class TransectProccessErrorMessage(PMGErrorMessage):
	def __init__(self, error_message, traceback_info):
		super(TransectProccessErrorMessage, self).__init__(error_message, traceback_info)
		self.error_message = "%s file %s" % (self.error_message, self.file_name)