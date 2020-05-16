from __future__ import absolute_import, division, print_function, unicode_literals
import os, nilearn, time, math, reader, time, csv, random, config
os.environ["CUDA_VISIBLE_DEVICES"] = "-1" # Ask tensorflow to not use GPU
import SimpleITK as sitk
import numpy as np
from numpy import asarray
import tensorflow as tf
import nibabel as nib
import plotly.graph_objects as go
from nilearn import image, plotting, datasets, surface
from nilearn.input_data import NiftiMasker
from keras.utils import to_categorical
from keras import models
from keras.optimizers import SGD
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D # for 3d plotting
from tensorflow.keras import Model
from tensorflow.keras import backend as K
from tensorflow.keras.layers import Dense, Flatten, Conv3D, LeakyReLU
from random import randint, randrange

class KleinNet:

	def __init__(self):
		print("\n - KleinNet Initialized -\n - Process PID - " + str(os.getpid()) + ' -\n')
		os.chdir('../..')
		print('Current working directory change to ' + os.getcwd() + '\n')


	def run(self):
		self.create_dir()
		self.wrangle()
		self.check()
		self.build()
		self.train()
		self.test()
		self.plot_accuracy()
		self.observe(0)
		self.observe(1)

	def optimize(self):
		alpha_opt = [0.1, 0.01, 0.001, 0.0001]
		epsilon_opt = [1e-5, 1e-6, 1e-7, 1e-8]
		learning_rate_opt = [0.001, 1e-4, 1e-5, 1e-6]
		bias_init_opt = [0, 0.01, self.optimum_bias()]
		index = 1
		for self.alpha in alpha_opt:
			for self.epsilon in epsilon_opt:
				for self.learning_rate in learning_rate_opt:
					for self.bias_init in bias_init_opt:
						self.build()
						self.train()
						self.test()
						self.plot_accuracy(index)
						index += 1

	def jack_knife(self):
		for jackknife in range(1, config.subject_count):
			subject_range = range(config.subject_count)
			np.delete(subject_range, jackknife)
			self.wrangle(subject_range)
			self.build()
			self.train()
			self.test()
		return

	def observe(self, interest):
		try:
			chdir(config.result_directory + config.run_directory + '/')
			chdir('../..')
		except:
			os.mkdir(config.result_directory + config.run_directory + '/')
		try:
			self.images
		except:
			self.wrangle_subject(1)
		while self.sample_label != interest: # Grab next sample that is the other category
			ind = random.randint(self.images.shape[0])
			self.sample_label = self.labels[ind] # Grab sample label
		self.sample = self.images[ind, :, :, :, :] # Grab sample volume
		#self.anatomie = self.anatomies[ind]
		self.header = self.headers[ind]
		if sample_label == 0: # Define sample label for display
			self.category = 'Incorrect'
		if sample_label == 1:
			self.category = "Correct"
		self.extract(self.model, sample.reshape(1, config.x_size, config.y_size, config.z_size, 1), category, header, anatomie)

	def optimum_bias(self):
		if correct < incorrect:
			return math.log((config.correct/config.incorrect), (2.78))
		else:
			return math.log((config.incorrect/config.correct), (2.78))

	def orient(self):
		print("\nOrienting and generating KleinNet lexicons")
		self.subject_IDs = ["sub-" + '0'*(config.ID_len - len(str(ind))) + str(ind) for ind in range(1, config.subject_count + 1)]
		self.numpy_folders = [config.data_directory  + subject_ID + '/' + config.numpy_output_dir + '/' for subject_ID in self.subject_IDs]
		self.volumes_filenames = [subject + "_volumes.npy" for subject in self.subject_IDs]
		self.labels_filenames = [subject + "_labels.npy" for subject in self.subject_IDs]
		self.header_filenames = [subject + "_headers.npy" for subject in self.subject_IDs]
		self.affines_filenames = [subject + "_affines.npy" for subject in self.subject_IDs]
		self.anat_folders = [config.data_directory + subject_ID + '/anat/' for subject_ID in self.subject_IDs]
		self.anat_filenames = [subject_ID + "_T1w.nii" for subject_ID in self.subject_IDs]



	def wrangle_all(self, subject_range = range(config.subject_count), jackknife = None):
		try:
			self.numpy_folders
		except:
			self.orient()
		self.progressbar(0, (config.subject_count - 1), prefix = 'Wrangling Data', suffix = 'Complete', length = 40)
		for subject_index in subject_range:
			if subject_index != jackknife:
				image = np.load(self.numpy_folders[subject_index] + self.volumes_filenames[subject_index]) # Load data
				if config.wumbo == False:
					label = np.load(self.numpy_folders[subject_index] + self.labels_filenames[subject_index])
				else:
					label = np.random.randint(2, size = images.shape[0])
				try:
					images = np.append(images, image, axis = 0)
					labels = np.append(labels, label)
				except:
					images = image
					labels = label
			self.progressbar(subject_index, (config.subject_count - 1), prefix = 'Wrangling Data', suffix = 'Complete', length = 40)
		print("\n")
		if jackknife == None:
			self.x_train = images[:(round((images.shape[0]/3)*2)),:,:,:]
			self.y_train = labels[:(round((len(labels)/3)*2))]
			self.x_test = images[(round((images.shape[0]/3)*2)):,:,:,:]
			self.y_test = labels[(round((len(labels)/3)*2)):]
		else:
			self.x_train = images
			self.y_train = labels
			self.x_test = np.load(self.numpy_folders[jackknife - 1] + self.volumes_filenames[jackknife - 1])
			self.y_test = np.load(self.numpy_folders[jackknife - 1] + self.labels_filenames[jackknife - 1])

	def wrangle_subject(self, subject_number):
		try:
			self.numpy_folders
		except:
			self.orient()
		self.anatomies = nib.load(self.anat_folders[subject_number - 1] + self.anat_filenames[subject_number - 1])
		self.headers = np.load(self.numpy_folders[subject_number - 1] + self.header_filenames[subject_number - 1], allow_pickle = True)
		self.images = np.load(self.numpy_folders[subject_number - 1] + self.volumes_filenames[subject_number - 1]) # Load data
		if config.wumbo == False:
			self.labels = np.load(self.numpy_folders[subject_number - 1] + self.labels_filenames[subject_number - 1])
		else:
			self.labels = np.random.randint(2, size = images.shape[0])

	# Create label vector for subject
	def check(self):
		print('\nDescribing testing and training data...\nLabel length - ' + str(len(self.labels)) + '\nImages shape - ' + str(self.images.shape))
		assert(len(self.x_train) == len(self.y_train) and len(self.x_test) == len(self.y_test))

	def calcConv(self, shape):
		return [round(((input_length - filter_length + (2*pad))/stride) + 1) for input_length, filter_length, stride, pad in zip(shape, config.kernel_size, config.kernel_stride, config.padding)]

	def calcMaxPool(self, shape):
		return [round((input_length - pool_length + (2*pad))/stride + 1) for input_length, pool_length, stride, pad in zip(shape, config.pool_size, config.pool_stride, config.padding)]

	def calcConvTrans(self, shape):
		if config.zero_padding == 'valid':
			return [round((input_length - 1)*stride + filter_length) for input_length, filter_length, stride in zip(shape, config.kernel_size, config.kernel_stride)]
		else:
			return [round(input_length*stride) for input_length, filter_length, stride in zip(shape, config.kernel_size, config.kernel_stride)]

	def calcUpSample(self, shape):
		return [round((input_length - 1)*(filter_length/stride)*2) for input_length, filter_length, stride in zip(shape, config.pool_size, config.pool_stride)]

	def plan(self):
		print("\nPlanning KleinNet model structure")
		self.filter_counts = []
		convolution_size = config.init_filter_count
		for depth in range(config.convolution_depth*2):
			self.filter_counts.append(convolution_size)
			convolution_size = convolution_size*2

		self.layer_shapes = []
		self.output_layers = []
		conv_shape = [config.x_size, config.y_size, config.z_size]
		conv_layer = 1
		for depth in range(config.convolution_depth):
			conv_shape = self.calcConv(conv_shape)
			self.layer_shapes.append(conv_shape)
			self.output_layers.append(conv_layer)
			conv_layer += 3
			conv_shape = self.calcConv(conv_shape)
			self.layer_shapes.append(conv_shape)
			self.output_layers.append(conv_layer)
			conv_layer += 4
			if depth < config.convolution_depth - 1:
				conv_shape = self.calcMaxPool(conv_shape)

		self.new_shapes = []
		for layer_ind, conv_shape in enumerate(self.layer_shapes):
			new_shape = self.calcConvTrans(conv_shape)
			for layer in range(layer_ind,  0, -1):
				new_shape = self.calcConvTrans(new_shape)
				if layer % 2 == 1 & layer != 1:
					new_shape = self.calcUpSample(new_shape)
			self.new_shapes.append(new_shape)

		for layer, plan in enumerate(zip(self.output_layers, self.filter_counts, self.layer_shapes, self.new_shapes)):
			print("Layer ", layer + 1, " (", plan[0], ")| Filter count:", plan[1], "| Layer Shape: ", plan[2], "| Deconvolution Output: ", plan[3])

	def build(self):
		try:
			self.filter_counts
		except:
			self.plan()
		print('\nConstructing KleinNet model')
		self.model = tf.keras.models.Sequential() # Create first convolutional layer
		for layer in range(1, config.convolution_depth + 1): # Build the layer on convolutions based on config convolution depth indicated
			self.model.add(tf.keras.layers.Conv3D(self.filter_counts[layer*2 - 2], config.kernel_size, strides = config.kernel_stride, padding = config.zero_padding, input_shape = (config.x_size, config.y_size, config.z_size, 1), use_bias = True, kernel_initializer = config.kernel_initializer, bias_initializer = tf.keras.initializers.Constant(config.bias)))
			self.model.add(LeakyReLU(alpha = config.alpha))
			self.model.add(tf.keras.layers.BatchNormalization())
			self.model.add(tf.keras.layers.Conv3D(self.filter_counts[layer*2 - 1], config.kernel_size, strides = config.kernel_stride, padding = config.zero_padding, use_bias = True, kernel_initializer = config.kernel_initializer, bias_initializer = tf.keras.initializers.Constant(config.bias)))
			self.model.add(LeakyReLU(alpha = config.alpha))
			self.model.add(tf.keras.layers.BatchNormalization())
			if layer < config.convolution_depth:
				self.model.add(tf.keras.layers.MaxPooling3D(pool_size = config.pool_size, strides = config.pool_stride, padding = config.zero_padding, data_format = "channels_last"))
		if config.density_dropout[0] == True: # Add dropout between convolution and density layer
			self.model.add(tf.keras.layers.Dropout(config.dropout))
		self.model.add(tf.keras.layers.Flatten()) # Create heavy top density layers
		for density, dense_dropout in zip(config.top_density, config.density_dropout[1:]):
			self.model.add(tf.keras.layers.Dense(density, use_bias = True, kernel_initializer = config.kernel_initializer, bias_initializer = tf.keras.initializers.Constant(config.bias))) # Density layer based on population size of V1 based on Full-density multi-scale account of structure and dynamics of macaque visual cortex by Albada et al.
			self.model.add(LeakyReLU(alpha = config.alpha))
			if dense_dropout == True:
				self.model.add(tf.keras.layers.Dropout(config.dropout))
		self.model.add(tf.keras.layers.Dense(1, activation='sigmoid')) #Create output layer
		self.model.build()
		self.model.summary()

		if config.optimizer == 'Adam':
			optimizer = tf.keras.optimizers.Adam(learning_rate = config.learning_rate, epsilon = config.epsilon, amsgrad = config.use_amsgrad)
		if config.optimizer == 'SGD':
			optimizer = tf.keras.optimizers.SGD(learning_rate = config.learning_rate, momentum = config.momentum, nesterov = config.use_nestrov)
		self.model.compile(optimizer = optimizer, loss = 'binary_crossentropy', metrics = ['accuracy']) # Compile model and run
		print('\nKleinNet model compiled using', config.optimizer)

	def train(self):
		self.history = self.model.fit(self.x_train, self.y_train, epochs = config.epochs, batch_size = config.batch_size, validation_data = (self.x_test, self.y_test))

	def test(self):
		self.loss, self.accuracy = self.model.evaluate(self.x_test,  self.y_test, verbose=2)

	def save(self):
		tf.save_model.save(self.model, 'Model_Description') # Save model

	def extract(self, sample, category, header, anatomie):
		print("\nExtracting " + category + " answer features from KleinNet convolutional layers...")
		layer_outputs = [layer.output for layer in self.model.layers[:]]
		activation_model_1 = tf.keras.models.Model(inputs = self.model.input, outputs = [layer_outputs[1], self.model.output]) # Redesign model to output after first layer
		activation_model_2 = tf.keras.models.Model(inputs = self.model.input, outputs = [layer_outputs[4], self.model.output])
		activation_model_3 = tf.keras.models.Model(inputs = self.model.input, outputs = [layer_outputs[8], self.model.output])
		activation_model_4 = tf.keras.models.Model(inputs = self.model.input, outputs = [layer_outputs[11], self.model.output])

		deconv_model_1 = tf.keras.models.Sequential()
		deconv_model_1.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, input_shape = (63, 63, 28, 1), kernel_initializer = tf.keras.initializers.Ones()))

		deconv_model_2 = tf.keras.models.Sequential()
		deconv_model_2.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, input_shape = (62, 62, 27, 1), kernel_initializer = tf.keras.initializers.Ones()))
		deconv_model_2.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, kernel_initializer = tf.keras.initializers.Ones()))

		deconv_model_3 = tf.keras.models.Sequential()
		deconv_model_3.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, input_shape = (30, 30, 12, 1), kernel_initializer = tf.keras.initializers.Ones()))
		deconv_model_3.add(tf.keras.layers.UpSampling3D(size = config.pool_size, strides = config.pool_stride, data_format = 'channels_last'))
		deconv_model_3.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, kernel_initializer = tf.keras.initializers.Ones()))
		deconv_model_3.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, kernel_initializer = tf.keras.initializers.Ones()))

		deconv_model_4 = tf.keras.models.Sequential()
		deconv_model_4.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, input_shape = (29, 29, 11, 1), kernel_initializer = tf.keras.initializers.Ones()))
		deconv_model_4.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, kernel_initializer = tf.keras.initializers.Ones()))
		deconv_model_4.add(tf.keras.layers.UpSampling3D(size = config.pool_size, strides = config.pool_stride, data_format = 'channels_last'))
		deconv_model_4.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, kernel_initializer = tf.keras.initializers.Ones()))
		deconv_model_4.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, kernel_initializer = tf.keras.initializers.Ones()))

		CreateLayerFeatures(activation_model_1, deconv_model_1, sample, [63, 63, 28, 16], [64, 64, 29], category, "Layer_1", "Layer 1", header, anatomie)
		CreateLayerFeatures(activation_model_2, deconv_model_2, sample, [62, 62, 27, 32], [64, 64, 29], category, "Layer_2", "Layer 2", header, anatomie)
		CreateLayerFeatures(activation_model_3, deconv_model_3, sample, [30, 30, 12, 64], [64, 64, 28], category, "Layer_3", "Layer 3", header, anatomie)
		CreateLayerFeatures(activation_model_4, deconv_model_4, sample, [29, 29, 11, 128], [64, 64, 28], category, "Layer_4", "Layer 4", header, anatomie)
		return

	def new_extract(self):
		self.output_layers, self.filter_counts, self.layer_shapes, self.new_shapes
		layer_outputs = [layer.output for layer in self.model.layers[:]]

		for self.layer in range(1, (config.convolution_depth*2 + 1)): # Build deconvolutional models for each layer
			self.activation_model = tf.keras.models.Model(inputs = self.model.input, outputs = [layer_outputs[self.output_layers[self.layer - 1]], self.model.output])
			self.deconv_model = tf.keras.models.Sequential() # Create first convolutional layer
			self.deconv_model.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, input_shape = (self.layer_shapes[self.layer - 1][0], self.layer_shapes[self.layer - 1][1], self.layer_shapes[self.layer - 1][2], 1), kernel_initializer = tf.keras.initializers.Ones()))
			for deconv_layer in range(self.layer - 1, 0, -1): # Build the depths of the deconvolution model
				if deconv_layer % 2 == 1 & deconv_layer != 1:
					self.deconv_model.add(tf.keras.layers.UpSampling3D(size = config.pool_size, data_format = 'channels_last'))
				self.deconv_model.add(tf.keras.layers.Conv3DTranspose(1, config.kernel_size, strides = config.kernel_stride, kernel_initializer = tf.keras.initializers.Ones()))
			print('Summarizing layer ', layer, ' deconvolution model')
			self.deconv_model.build()
			self.deconv_model.summary()


	def CreateLayerFeatures(self, activation_model, deconv_model, sample, current_shape, new_shape, category, Dir, Layer, Layer_name, header, anatomie):
		self.feature_maps, predictions = activation_model.predict(sample) # Grab feature map using single volume
		self.feature_maps = self.feature_maps[0, :, :, : ,:].reshape(self.current_shape[0], self.current_shape[1], self.current_shape[2], self.current_shape[3])

		self.progressbar(0, self.feature_maps.shape[3] - 1, prefix = 'Extracting Layer ' + str(self.layer) + ' Features', suffix = 'Complete', length = 40)
		for self.map_index in range(self.feature_maps.shape[3]): # Save feature maps in glass brain visualization pictures
			feature_map = (self.feature_maps[:, :, :, map_index].reshape(self.current_shape[0], self.current_shape[1], self.current_shape[2])) # Grab Feature map
			deconv_feature_map = self.deconv_model.predict(self.feature_maps[:, :, :, map_index].reshape(1, self.current_shape[0], self.current_shape[1], self.current_shape[2], 1)).reshape(self.new_shape[0], self.new_shape[1], self.new_shape[2])
			#self.glassBrain(deconv_feature_map, header, category, map_index, "DeConv", config.result_directory + config.run_directory + '/', Layer, Layer_name)
			#self.statMap(deconv_feature_map, anatomie, header, category, map_index, "DeConv", config.result_directory + config.run_directory + '/', Layer, Layer_name)
			self.surfStatMap(deconv_feature_map, header, category, map_index, "DeConv", config.result_directory + config.run_directory + '/', Layer, Layer_name)
			self.progressbar(map_index, self.feature_maps.shape[3] - 1, prefix = 'Extracting Layer ' + str(self.layer) + ' Features', suffix = 'Complete', length = 40)

		print("\n\nExtracting KleinNet model class activation maps")
		with tf.GradientTape() as gtape: # Create CAM
			conv_output, predictions = activation_model(sample)
			loss = predictions[:, np.argmax(predictions[0])]
			grads = gtape.gradient(loss, conv_output)
			pooled_grads = K.mean(grads, axis = (0, 1, 2, 3))

		heatmap = tf.math.reduce_mean((pooled_grads * conv_output), axis = -1)
		heatmap = np.maximum(heatmap, 0)
		max_heat = np.max(heatmap)
		if max_heat == 0:
			max_heat = 1e-10
		heatmap /= max_heat

		# Deconvolute heatmaps and visualize
		heatmap = deconv_model.predict(heatmap.reshape(1, self.current_shape[0], self.current_shape[1], self.current_shape[2], 1)).reshape(self.new_shape[0], self.new_shape[1], self.new_shape[2])
		#self.glassBrain(heatmap, header, category, 1, "CAM", config.result_directory + config.run_directory + '/', Layer, Layer_name)
		#self.statMap(heatmap, anatomie, header, category, 1, "CAM", config.result_directory + config.run_directory + '/', Layer, Layer_name)
		self.surfStatMap(heatmap, header, category, 1, "CAM", config.result_directory + config.run_directory + '/', Layer, Layer_name)

	def plot_all(self, data, data_type, map = self.map_index):
		#self.glassBrain(data, data_type, map)
		#self.statMap(data, data_type, map)
		self.surfStatMap(data, data_type, map)

	def preparePlots(self, data, data_type, map):
		affine = sef.header.get_best_affine()
		max_value, min_value, mean_value, std_value = dataDescrition(feature_map)
		if category != 'CAM' and category != 'Layer_1':
			threshold = (mean_value + (std_value*2))
		else:
			threshold = 0
			intensity = 0.5
			feature_map = feature_map * intensity
		feature_map = nib.Nifti1Image(data, affine = self.affine, header = self.header) # Grab feature map
		title = layer + " " + data_type + " Map " + str(map) + " for  " + self.category + " Answer"
		return feature_map, title, threshold

	def glassBrain(self, data, data_type, map):
		feature_map, title, threshold = self.preparePlots(data, header, map_index, category, "Glass Brain", Layer_name)
		plotting.plot_glass_brain(stat_map_img = feature_map, black_bg = True, plot_abs = False, display_mode = 'lzry', title = title, threshold = threshold, annotate = True, output_file = (config.result_directory + config.run_directory + '/' + category + '_Feature_Maps_' + conv_status + '/' + Layer + '/GB/feature' + str(map_index) + '-' + category + 'category.png')) # Plot feature map using nilearn glass brain - Original threshold = (mean_value + (std_value*2))


	def statMap(self, data, data_type, map):
		feature_map, title, threshold = self.preparePlots(feature_map, header, map_index, category, "Stat", Layer_name)
		for display, title, cut_coord in zip(['z', 'x', 'y'], ['-zview-', '-xview-', '-yview-'], [6, 6, 6]):
			plotting.plot_stat_map(feature_map, bg_img = anatomie, display_mode = display, cut_coords = cut_coord, black_bg = True, title = title, threshold = threshold, annotate = True, output_file = (config.result_directory + config.run_directory + '/' + category + '_Feature_Maps_' + conv_status + '/' + Layer + '/SM/feature' + str(map_index) + title + category + 'category.png')) # Plot feature map using nilearn glass brain

	def surfStatMap(self, data, data_type, map):
		feature_map, title, threshold = self.preparePlots(data, header, map_index, category, "Surface Stat", Layer_name)
		fsaverage = datasets.fetch_surf_fsaverage()

		texture = surface.vol_to_surf(feature_map, fsaverage.pial_left)
		plotting.plot_surf_stat_map(fsaverage.infl_left, texture, hemi = 'left', view = 'lateral', title = title, colorbar = True, threshold = threshold, bg_map = fsaverage.sulc_left, bg_on_data = True, cmap='Spectral', output_file = (config.result_directory + config.run_directory + "/" + category + '_Feature_Maps_' + conv_status + '/' + Layer + '/SSM/feature' + str(map_index) + '-left-lateral-' + category + 'category.png'))
		plotting.plot_surf_stat_map(fsaverage.infl_left, texture, hemi = 'left', view = 'medial', title = title, colorbar = True, threshold = threshold, bg_map = fsaverage.sulc_left, bg_on_data = True, cmap='Spectral', output_file = (config.result_directory + config.run_directory + '/' + category + '_Feature_Maps_' + conv_status + '/' + Layer + '/SSM/feature' + str(map_index) + '-left-medial-' + category + 'category.png'))

		texture = surface.vol_to_surf(feature_map, fsaverage.pial_right)
		plotting.plot_surf_stat_map(fsaverage.infl_right, texture, hemi = 'right', view = 'lateral', title = title, colorbar = True, threshold = threshold, bg_map = fsaverage.sulc_right, bg_on_data = True, cmap='Spectral', output_file = ( config.result_directory + config.run_directory + '/' + category + '_Feature_Maps_' + conv_status + '/' + Layer + '/SSM/feature' + str(map_index) + '-right-lateral-' + category + 'category.png'))
		plotting.plot_surf_stat_map(fsaverage.infl_right, texture, hemi = 'right', view = 'medial', title = title, colorbar = True, threshold = threshold, bg_map = fsaverage.sulc_right, bg_on_data = True, cmap='Spectral', output_file = (config.result_directory + config.run_directory + '/' + category + '_Feature_Maps_' + conv_status + '/' + Layer + '/SSM/feature' + str(map_index) + '-right-medial-' + category + 'category.png'))

	def plot_accuracy(self, i = 1):
		print("\nEvaluating KleinNet model accuracy & loss...")
		# Evaluate the model accuracy
		plt.plot(self.history.history['accuracy'], label='Accuracy')
		plt.plot(self.history.history['val_accuracy'], label = 'Validation Accuracy')
		plt.xlabel('Epoch')
		plt.ylabel('Accuracy')
		plt.legend(loc='upper right')
		plt.ylim([0, 1])
		plt.title("~learnig rate - " + str(config.learning_rate) + " ~alpha-" + str(config.alpha) + " ~epsilon -" + str(config.epsilon) + ' ~bias-' + str(config.bias) )
		plt.savefig(config.result_directory + config.run_directory + "/Model_Description/Model_" + str(i + 1) + "_Accuracy.png")
		plt.close()

		#Evaluate model loss
		plt.plot(history.history['loss'], label='Loss')
		plt.plot(history.history['val_loss'], label='Validation Loss')
		plt.xlabel('Epoch')
		plt.ylabel('Loss')
		plt.legend(loc='upper right')
		plt.title("~learnig rate - " + str(config.learning_rate) + " ~alpha-" + str(config.alpha) + " ~epsilon -" + str(config.epsilon) + ' ~bias-' + str(config.bias) )
		plt.savefig(config.result_directory + config.run_directory + "/Model_Description/Model_" + str(i + 1) + "_Loss.png")
		plt.close()


	def create_dir(self, first_dir = ['Correct_Feature_Maps_DeConv', 'Correct_Feature_Maps_CAM', 'Incorrect_Feature_Maps_DeConv', 'Incorrect_Feature_Maps_CAM' ], second_dir = ['Layer_1', 'Layer_2', 'Layer_3', 'Layer_4'], third_dir = ['GB', 'SM', 'SSM']):
		os.mkdir(config.result_directory + config.run_directory + '/')
		os.mkdir(config.result_directory + config.run_directory + "/Model_Description")
		for first in first_dir:
			os.mkdir(config.result_directory + config.run_directory + "/" + first)
			for layer_count in second_dir:
				os.mkdir(config.result_directory + config.run_directory + "/" + first + "/" + second)
				for third in third_dir:
					os.mkdir(config.result_directory + config.run_directory + "/" + first + "/" + second + "/" + third)

	def progressbar (self, iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
		percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
		filledLength = int(length * iteration // total)
		bar = fill * filledLength + '-' * (length - filledLength)
		print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = printEnd)
		if iteration == total:
		    print()