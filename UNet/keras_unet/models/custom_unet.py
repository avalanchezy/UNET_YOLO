from tensorflow.keras.models import Model
from tensorflow.keras.layers import BatchNormalization, Conv2D, Conv2DTranspose, MaxPooling2D, Dropout, SpatialDropout2D, UpSampling2D, Input, concatenate, LeakyReLU


def upsample_conv(inputs, filters, kernel_size, strides, padding, activation=None, kernel_initializer='he_normal', kernel_regularizer='None'):
    return Conv2DTranspose(filters, kernel_size, strides=strides, padding=padding, activation=activation, kernel_initializer=kernel_initializer)(inputs)

def upsample_simple(inputs, filters, kernel_size, strides, padding, activation=None, kernel_initializer='he_normal', kernel_regularizer='None'):
    return UpSampling2D(strides)(inputs)
    #x=UpSampling2D(strides)(inputs)
    #return  Conv2D(filters, kernel_size, activation=activation, kernel_initializer=kernel_initializer, padding=padding, kernel_regularizer=kernel_regularizer)(x)


def dropout_simple(rate, data_format='channels_last'):
    return Dropout(rate)   

def dropout_spatial(rate, data_format='channels_last'):
    return SpatialDropout2D(rate=rate, data_format=data_format)


def conv2d_block(
    inputs, 
    use_batch_norm=True, 
    dropout=0.3, 
    filters=16, 
    kernel_size=(3,3), 
    activation='relu',   # LeakyReLU, elu, relu, 
    padding='same',
    dropout_type='spatial', #spatial  simple
    kernel_initializer='he_normal',  # 'glorot_uniform'
    kernel_regularizer='None'):
    
    if dropout_type=='spatial':
        dropout_type = dropout_spatial
    else:
        dropout_type = dropout_simple
        
    if activation != "LeakyReLU":
        c = Conv2D(filters, kernel_size, activation=activation, kernel_initializer=kernel_initializer, padding=padding, kernel_regularizer=kernel_regularizer) (inputs)
    else:  #leaky ReLU needs a layer...
        c = Conv2D(filters, kernel_size, activation=None, kernel_initializer=kernel_initializer, padding=padding, kernel_regularizer=kernel_regularizer) (inputs)           
    if use_batch_norm:
        c = BatchNormalization()(c)
    
    if activation == "LeakyReLU":
        c = LeakyReLU()(c)

    if dropout > 0.0:
        c = dropout_type(rate=dropout, data_format='channels_last')(c)   

    if activation != "LeakyReLU":
        c = Conv2D(filters, kernel_size, activation=activation, kernel_initializer=kernel_initializer, padding=padding, kernel_regularizer=kernel_regularizer) (c)
    else:
        c = Conv2D(filters, kernel_size, activation=None, kernel_initializer=kernel_initializer, padding=padding, kernel_regularizer=kernel_regularizer) (c)
    if use_batch_norm:
        c = BatchNormalization()(c)
    if activation=="LeakyReLU":
        c = LeakyReLU()(c)    

    if dropout > 0.0:
        c = dropout_type(rate=dropout, data_format='channels_last')(c)        
    return c



def custom_unet(
    input_shape,
    num_classes=1,
    use_batch_norm=True, 
    upsample_mode='deconv', # 'deconv' or 'simple' 
    use_dropout_on_upsampling=False, 
    dropout=0.3, 
    dropout_change_per_layer=0.0,
    filters=16,
    num_layers=4,
    kernel_size=(3,3),
    cnn_activation='relu', # 'LeakyReLU', 'elu', 'relu',... 
    output_activation='softmax', # 'sigmoid' or 'softmax'
    dropout_type='spatial', # spatial  simple
    kernel_initializer='he_normal',
    kernel_regularizer='None'):  
    
    if upsample_mode=='deconv':
        upsample=upsample_conv
    else:
        upsample=upsample_simple

    # Build U-Net model
    inputs = Input(input_shape)
    x = inputs   

    down_layers = []
    for l in range(num_layers):
        x = conv2d_block(inputs=x, filters=filters, kernel_size=kernel_size, activation=cnn_activation, use_batch_norm=use_batch_norm, dropout=dropout, dropout_type=dropout_type, kernel_initializer=kernel_initializer, kernel_regularizer=kernel_regularizer)
        down_layers.append(x)
        x = MaxPooling2D((2, 2)) (x)
        dropout = dropout + dropout_change_per_layer
        filters = filters*2 # double the number of filters with each layer

    x = conv2d_block(inputs=x, filters=filters, activation=cnn_activation, use_batch_norm=use_batch_norm, dropout=dropout, dropout_type=dropout_type, kernel_initializer=kernel_initializer, kernel_regularizer=kernel_regularizer)

    if not use_dropout_on_upsampling:
        dropout = 0.0
        dropout_change_per_layer = 0.0

    for conv in reversed(down_layers):        
        filters //= 2 # decreasing number of filters with each layer 
        dropout = dropout - dropout_change_per_layer
        x = upsample(inputs=x, filters=filters, kernel_size=(2, 2), strides=(2, 2), padding='same', activation=cnn_activation, kernel_initializer=kernel_initializer, )
        x = concatenate([x, conv])
        x = conv2d_block(inputs=x, filters=filters, activation=cnn_activation, use_batch_norm=use_batch_norm, dropout=dropout, dropout_type=dropout_type, kernel_initializer=kernel_initializer, kernel_regularizer=kernel_regularizer)
    
    outputs = Conv2D(num_classes, (1, 1), activation=output_activation) (x)    
    
    model = Model(inputs=[inputs], outputs=[outputs])
    return model