# -*- coding: utf-8 -*-
"""04_Neural_Network_Designs.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1CfqYIfbDlAV62ueQgcWgFlmo0DGxZ70k

## Building the architectures for the Neural Networks

This script does the following: 
1. Defines three different Neural Networks
    
  1. **CNN1**: CNN without batch normalization
  2. **CNN2**: CNN with batch normalization
  2. **ResNet** 
2. Defines functions for compiling and displaying the model
3. Handles data generation

**Author**: Soumya Shreeram <br>
**Script adapted from**: Millon Martin & Kevin Müller <br>
**Date**: 16th March 2020

## 1. Imports
"""

from google.colab import drive
import os
import pickle

import numpy as np
import matplotlib.pyplot as plt
import random
from IPython.display import Image

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

import tensorflow as tf

from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Activation, InputSpec
from tensorflow.python.keras.layers import Conv1D, Conv2D
from tensorflow.python.keras.layers import MaxPooling1D, MaxPooling2D, GlobalMaxPooling2D
from tensorflow.keras.layers import Dense, Dropout, Flatten, Add, BatchNormalization, Concatenate
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.utils import plot_model
from tensorflow.keras import backend as K
from tensorflow.keras.layers import Layer

"""### 2. Defines a modified pooling layer that outputs a 3D tensor

Note: the `keras.layers.GLobalMaxPooling2D` returns a 2D tensor of shape: `(batch_size, channels)`. However, this pooling layer outputs a shape: `(batch_size, channels, rows or cols)` based on the input of data format.
"""

class GlobalMaxPoolingSp2D(Layer):
    """Global max pooling operation for spatial data along a single dimension.
    # Arguments
        sqash_dim: A scalar
            1: Find the maximum along the columns (the output doesn't the row dimension)
            2: Find the maximum along the rows (the output doesn't the column dimension)
            Defaults: squash_dim=2
        data_format: A string,
            one of `channels_last` (default) or `channels_first`.
            The ordering of the dimensions in the inputs.
            `channels_last` corresponds to inputs with shape
            `(batch, height, width, channels)` while `channels_first`
            corresponds to inputs with shape
            `(batch, channels, height, width)`.
            It defaults to the `image_data_format` value found in your
            Keras config file at `~/.keras/keras.json`.
            If you never set it, then it will be "channels_last".
    # Input shape
        - If `data_format='channels_last'`:
            4D tensor with shape:
            `(batch_size, rows, cols, channels)`
        - If `data_format='channels_first'`:
            4D tensor with shape:
            `(batch_size, channels, rows, cols)`
    # Output shape
        - If `data_format='channels_last'`:
            3D tensor with shape:
            `(batch_size, rows or cols, channels)`
        - If `data_format='channels_last'`:
            3D tensor with shape:
            `(batch_size, channels, rows or cols)`
    """
    
  
    def __init__(self, squash_dim=2, data_format=None, **kwargs):
        if data_format is None:
          data_format = K.image_data_format()
        data_format = data_format.lower()
        if data_format not in {'channels_first', 'channels_last'}:
          raise ValueError('The `data_format` argument must be one of '
                           '"channels_first", "channels_last". Received: ' +
                           str(value))
        self.data_format = data_format
        
        self.input_spec = InputSpec(ndim=4)
        self.squash_dim = squash_dim
        super(GlobalMaxPoolingSp2D, self).__init__(**kwargs)

    def compute_output_shape(self, input_shape):
        if self.data_format == 'channels_last':
            return (input_shape[0], input_shape[3-self.squash_dim], input_shape[3])
        else:
            return (input_shape[0], input_shape[1], input_shape[4-self.squash_dim])

    def call(self, inputs):
        if self.data_format == 'channels_last':
            return K.max(inputs, axis=self.squash_dim)
        else:
            return K.max(inputs, axis=self.squash_dim+1)
      
    def get_config(self):
        config = {'data_format': self.data_format}
        base_config = super(GlobalMaxPoolingSp2D, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

"""General functions used to add:
*   convolutional layers
*   max pooling layers
*   fully connected layers
"""

def addConvolutionalLayers(output, num_pix, num_filter, kernel_size, API=True):
  """
  Function to add convolutional and max pooling layers to the model
  @params defined in the main CNN function buildModel---()
  @API :: boolean that decides wether to add layers sequenctially or using API
  """
  if API:
    kernel_size = (kernel_size, 1)
    conv = Conv2D(num_filter, kernel_size, strides= (1,1),\
                      padding='same')(output) 
    output = Activation('relu')(conv)
  # adds layers sequentially
  else: 
    in_shape = (num_pix, None, 1) 
    kernel_size = (kernel_size, 1)
    strides = (1,1)
    # adds convolutional layers
    output.add(Conv2D(num_filter, kernel_size, strides=strides, \
                    padding='same', input_shape = in_shape, activation='relu'))
  return output

def addPoolingLayers(output, maxpoolsize, API=True):
  """
  Function adds pooling layers to the CNN
  @output :: output from the layer
  @maxpoolsize :: pool size value
  @API :: boolean that decides wether to add layers sequenctially or using API
  """
  if maxpoolsize is not None:
    if API:
      poolsize = (maxpoolsize,1)
      output = MaxPooling2D(pool_size=poolsize, strides =(maxpoolsize,1))(output)       
    else:
      poolsize = (maxpoolsize,1)
      output.add(MaxPooling2D(pool_size=poolsize, strides =(maxpoolsize,1)))       
  return output

def addFullyConnectedLayers(output, num_hidden_nodes, dropout_ratio, r_0,\
                            API=True):
  """
  Function to add fully connected layers to the model
  @num_hidden_nodes :: no. of nodes in the layers prior to the output layer
  @dropout_ratio :: weight constrain in the dropout layers
  @r_0 :: len(r_0) defines the no. of nodes in the output layer
  @API :: boolean that decides wether to add layers sequenctially or using API
  """
  # post CNN; fully connected layers
  for i, nodes in enumerate(num_hidden_nodes):
    if API:
      hidden = Dense(nodes, activation='sigmoid')(output)
      activ = Activation('sigmoid')(hidden)
      output = Dropout(dropout_ratio)(hidden)    
    else:
      output.add(Dense(nodes, activation='sigmoid'))
      output.add(Dropout(dropout_ratio))
  return output

"""## 3. Neural Network Architectures

### 3.1 Convolutional Neural Network: Design 1

The following uses the `keras` Sequential models
"""

def buildModelCNN1(num_pix, num_filter, kernel_size, maxpoolsize,\
                   num_hidden_nodes, r_0):
  """
  Function to build the model architecture, set optimizers and compile the model 
  @num_pix :: used to define the shape of the input layer
  @num_filter :: arr with the ascending order of filters in the conv2D layers
  @kernel_size :: arr with the kernel sizes for the corresponding conv2D layers
  @maxpoolsize :: arr with the pool sizes for the corresponding conv2D layers
  @num_hidden_nodes :: no. of nodes in the FNN layer right after the CNN
  @r_0 :: array of all the scale radii
  
  @Returns:: model
  """
  model = Sequential()
  
  # adding convolutional and pooling layers
  model = addConvolutionalLayers(model, num_pix, num_filter, kernel_size, API=False)
  model = addPoolingLayers(model, maxpoolsize, API=False)
  model.add(GlobalMaxPoolingSp2D())
  model.add(Flatten())
  
  # fully connected layers; added dropout these layer with weight constraint
  model = addFullyConnectedLayers(model, num_pix, num_hidden_nodes,\
                                  dropout_ratio, r_0, API=False)
  # final output layer
  model.add(Dense(len(r_0), activation='softmax'))
  
  return model

"""### 3.2 Convolutional Neural Network: Design 2

This CNN accounts for batch normalization unlike the first case. Additionally, used Keras functional API for more flexibitity.
"""

def builfModelCNN2(num_pix, num_filter, kernel_size, maxpoolsize, num_hidden, \
                   dropout_ratio, shortcut, batch_norm, length_traj, r_0):
  """
  Function to build the model architecture, set optimizers and compile the model 
  @num_pix :: used to define the shape of the input layer  
  @num_filters :: arr with the ascending order of filters in the conv2D layers
  @kernel_size :: arr with the kernel sizes for the corresponding conv2D layers
  @maxpoolsize :: arr with the pool sizes for the corresponding conv2D layers
  @num_hidden_nodes :: no. of nodes in the FNN layer right after the CNN
  @dropout_ratio :: weight constrain on the dropout layer of the FNN 
  @shortcut :: arr that decides when to take the skip connections/shortcuts
  @bath_norm :: bool decided wether or not to normalize the output from a layer
  @r_0 :: array of all the scale radii
  
  @Returns:: model output
  """
  #input layer
  visible = Input(shape=(length_traj, None, 1))
  output = visible

  # skip connection variables
  execute_skip = False
  idx = 0

  for i in range(len(num_filter)):
    # shortcut path/ skip connection
    if shortcut and not execute_skip and shortcut[idx] == i:
      out_shortcut = output
      execute_skip = True
      idx += 1
    
    # feature extractors
    conv = addConvolutionalLayers(output, num_pix, num_filter[i], kernel_size[i],\
                                  API=True)
    # batch normalization, activation
    if batch_norm: 
      conv = BatchNormalization()(conv)  
    conv = Activation('selu')(conv)

    # execute skip connection
    if shortcut and execute_skip and shortcut[idx] == i:
      conv = Concatenate(3)([conv, out_shortcut])
      execute_skip = False
      idx += 1

    # adds max pooling layers
    conv = addPoolingLayers(conv, maxpoolsize[i], API=True)
    
  pool = GlobalMaxPoolingSp2D()(conv)
  flat = Flatten()(pool)
  
  # fully connected layers; added dropout these layer with weight constraint
  hidden = addFullyConnectedLayers(flat, num_hidden, dropout_ratio, r_0, \
                                  API=True)
  output = Dense(len(r_0))(hidden)
  output = Activation('softmax')(output)

  return visible, output

"""### 3.3 Residual neural network: ResNet"""

def buildModelResNet(num_pix, num_filter, kernel_size, n_block, maxpoolsize, num_hidden, \
                dropout_ratio, batch_norm):
  """
  Function to build the model architecture, set optimizers and compile the model 
  @num_pix :: used to define the shape of the input layer
  @num_filters :: arr with the ascending order of filters in the conv2D layers
  @kernel_size :: arr with the kernel sizes for the corresponding conv2D layers
  @n_block :: int decides the no. of conv layers
  @maxpoolsize :: arr with the pool sizes for the corresponding conv2D layers
  @num_hidden :: no. of nodes in the fully connected layer right after the CNN
  @dropout_ratio :: weight constrain on the dropout layer of the FNN 
  @bath_norm :: bool decided wether or not to normalize the output from a layer
  @r_0 :: array of all the scale radii
  
  @Returns:: model output
  """
  visible = Input(shape=(num_pix, None, 1))
  shortcut = visible

  for i in range(n_block):
    # adding convolutional layers
    conv = addConvolutionalLayers(output, num_pix, num_filter[i], kernel_size[i],\
                                    API=True)
    conv = Add()[conv,shortcut]

    # adds max pooling and normalizes the layer
    conv = addPoolingLayers(conv, maxpoolsize[i], API=True)
    if batch_norm: 
      conv = BatchNormalization()(conv)

    # skip connection redefined
    shortcut = conv

  pool = GlobalMaxPoolingSp2D()(conv)
  flat = Flatten()(pool)
  
  # fully connected layers; added dropout these layer with weight constraint
  hidden = addFullyConnectedLayers(flat, num_hidden_nodes, dropout_ratio, r_0, \
                                  API=True)
  output = Dense(len(r_0))(hidden)
  output = Activation('softmax')(output)
  
  return model

"""## 4. Compiling and displaying the mdoel"""

def compileDisplayNetwork(inputs, outputs, optimizer_type, loss, metrics,\
                          filename, do_print_summary):
  """
  Function compiles the model and displays model summary, graph
  @input, output :: input and output layer info from the NN
  @optimizer_type, loss, metrics :: arguments used for compiling the model
  @do_print_summary :: bool that decides wether or not to display the info about the model

  @Returns :: model
  """
  model = Model(inputs=inputs, outputs=outputs)
  model.compile(optimizer=optimizer_type, loss=loss, metrics=metrics)

  if do_print_summary:
    # summarize layers
    print(model.summary())
    # plot graph
    plot_model(model, to_file=filename+'.png')
    return model

"""## 5. Data generation"""

def compute_num_batch(data_out, num_inputs, batch_size, verbose):
  
  data_out_class = np.argmax(data_out, axis=1)
  num_class = data_out.shape[1]
  num_group = 0
  
  for m1 in range(num_class):
    num_group += np.floor(np.count_nonzero(data_out_class == m1)/num_inputs)
  
  if np.isinf(batch_size) or num_group < batch_size:
    batch_size = num_group
    num_batch = 1
    if verbose:
      print('A single batch per epoch. The batch size ({}) is smaller than intended!'.format(batch_size))
  else:
    num_batch = np.floor(num_group/batch_size)
    if verbose:
      print('{} batches per epoch'.format(num_batch))
    
  return int(num_batch), int(batch_size)

def data_generator(data_in, data_out, num_inputs, batch_size, num_batch):
  
  data_out_class = np.argmax(data_out, axis=1)
  num_class = data_out.shape[1]
  data_ind = np.arange(len(data_out))
  
  data_in_group = np.zeros((num_class, data_in.shape[1], num_inputs*data_in.shape[2], 1))
  
  while True:
    np.random.shuffle(data_ind)
    num_ele_per_class = np.zeros(num_class, dtype=int)
    cur_ind = 0 ;
    
    for m1 in range(num_batch):
      data_in_batch = np.zeros((batch_size, data_in.shape[1], num_inputs*data_in.shape[2], 1))
      data_out_batch = np.zeros((batch_size, data_out.shape[1]))
      
      for m2 in range(batch_size):
        while True:
          cur_class = data_out_class[data_ind[cur_ind]]
          first_ele = num_ele_per_class[cur_class]*data_in.shape[2]
          last_ele = first_ele + data_in.shape[2]
          data_in_group[cur_class, :, first_ele:last_ele, :] \
            = data_in[data_ind[cur_ind]]
          
          num_ele_per_class[cur_class] += 1
          cur_ind += 1
          
          if num_ele_per_class[cur_class] == num_inputs:
            num_ele_per_class[cur_class] = 0
            data_in_batch[m2] = data_in_group[cur_class]
            data_out_batch[m2] = data_out[data_ind[cur_ind - 1]]
            break
      
      yield data_in_batch, data_out_batch

def fit_model_generator(model, data_in, data_out, num_inputs = 1, batch_size = 50, \
                        epochs = 50, validation_split = 0.2, verbose = 1):
  
  if num_inputs == 1:
    if data_in.ndim == 3:
      history = model.fit(data_in.reshape(data_in.shape[0:2] + (1,) + (data_in.shape[2],)),\
                          data_out, batch_size=batch_size, epochs=epochs, \
                          verbose=verbose, validation_split=validation_split, shuffle=True)
    else:
      history = model.fit(data_in, data_out, batch_size=batch_size, epochs=epochs, \
                          verbose=verbose, validation_split=validation_split, shuffle=True)
  else:
    data_ind = np.arange(len(data_out))
    data_ind_train, data_ind_valid = train_test_split(data_ind, test_size=validation_split)
    
    num_batch_train, batch_size_train = compute_num_batch(data_out[data_ind_train],\
                                                    num_inputs, batch_size, True)
    num_batch_valid, batch_size_valid = compute_num_batch(data_out[data_ind_valid],\
                                                    num_inputs, np.inf, False)
    
    history = model.fit_generator( \
                generator = data_generator(data_in[data_ind_train], data_out[data_ind_train], \
                  num_inputs, batch_size_train, num_batch_train), \
                steps_per_epoch = num_batch_train, epochs = epochs, verbose =  verbose, \
                validation_data = data_generator(data_in[data_ind_valid], data_out[data_ind_valid], \
                  num_inputs, batch_size_valid, num_batch_valid), \
                validation_steps = num_batch_valid)
  
  
  return model, history

def evaluate_model(model, data_in, data_out, num_inputs = 1, verbose = 1):
  
  if num_inputs == 1:
    if data_in.ndim == 3:
      data_in = data_in.reshape(data_in.shape[0:2] + (1,) + (data_in.shape[2],))
  else:
    num_batch, batch_size = compute_num_batch(data_out, num_inputs, np.inf, False)
  
    data_gen = data_generator(data_in, data_out, num_inputs, batch_size, num_batch)
    data_in, data_out = next(data_gen)
  
  return model.evaluate(data_in, data_out, verbose = verbose)

def predict_model(model, data_in, data_out, num_inputs = 1, verbose = 0):
  
  if num_inputs == 1:
    if data_in.ndim == 3:
      data_in = data_in.reshape(data_in.shape[0:2] + (1,) + (data_in.shape[2],))
  else:
    num_batch, batch_size = compute_num_batch(data_out, num_inputs, np.inf, False)
    
    data_gen = data_generator(data_in, data_out, num_inputs, batch_size, num_batch)
    data_in, data_out = next(data_gen)
    
  data_predict = model.predict(data_in, verbose = verbose)
  
  return data_predict, data_out

"""## 6. Sample and cut trajectories"""

def prepare_data_sample_cut(data_in, sampling, num_pieces):
  
  reduced_shape = np.ceil(data_in.shape[1]/sampling) - 1
  length_piece = int(round(2*reduced_shape/(num_pieces + 1)))
  data_in_prep = np.zeros((len(data_in), length_piece, num_pieces, 1))
  
  for m1 in range(len(data_in)):
    cur_data = data_in[m1,0:data_in.shape[1]:sampling,0]#Sampling
    
    if m1 == 0:
      print(cur_data.shape)
    
    #The trajectory is cut such that half of the pieces is shared with each neighbor
    #For an array of length 8, if the array is cut into 3 pieces, the pieces are the following:
    #1 -> 0:3, 2 -> 2:5, 3 -> 4:7
    for m2 in range(num_pieces - 1):
      first_ele = int(round(m2*reduced_shape/(num_pieces + 1)))
      data_in_prep[m1,:,m2,0] = cur_data[first_ele : first_ele+length_piece]
    
    data_in_prep[m1,:,num_pieces-1,0] = cur_data[len(cur_data) - length_piece : len(cur_data)]
    
  return data_in_prep