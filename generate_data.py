import os
import skimage.transform
import time
import glob
import numpy as np
import mahotas
import random
import matplotlib
import matplotlib.pyplot as plt
import scipy
import scipy.ndimage
from scipy.ndimage.filters import maximum_filter

# the idea is to grow the labels to cover the whole membrane
# image and label should be [0,1]
def adjust_imprecise_boundaries(image, label, number_iterations=5):
    label = label.copy()
    label_orig = label.copy()

    for i in xrange(number_iterations):
        # grow labels by one pixel
        label = maximum_filter(label, 2)
        # only keep pixels that are on dark membrane
        non_valid_label = np.logical_and(label==1, image>0.7)
        label[non_valid_label] = 0

    # make sure original labels are preserved
    label = np.logical_or(label==1, label_orig==1)

    return label


def deform_images(image1, image2, image3=None):
    # assumes image is uint8
    def apply_deformation(image, coordinates):
        # ndimage expects uint8 otherwise introduces artifacts. Don't ask me why, its stupid.
        deformed = scipy.ndimage.map_coordinates(image, coordinates, mode='reflect')
        deformed = np.reshape(deformed, image.shape) 
        return deformed

    displacement_x = np.random.normal(size=image1.shape, scale=10)
    displacement_y = np.random.normal(size=image1.shape, scale=10)
    
    # smooth over image
    coords_x, coords_y = np.meshgrid(np.arange(0,image1.shape[0]), np.arange(0,image1.shape[1]), indexing='ij')

    displacement_x = coords_x.flatten() #+ scipy.ndimage.gaussian_filter(displacement_x, sigma=5).flatten()
    displacement_y = coords_y.flatten() #+ scipy.ndimage.gaussian_filter(displacement_y, sigma=5).flatten()
    
    coordinates = np.vstack([displacement_x, displacement_y])
    
    deformed1 = apply_deformation(np.uint8(image1*255), coordinates)
    deformed2 = apply_deformation(np.uint8(image2*255), coordinates)
    if not image3 is None:
        deformed3 = apply_deformation(image3, coordinates)
        return (deformed1, deformed2, deformed3)

    return (deformed1, deformed2)


def deform_images_list(images):
    # assumes image is uint8
    def apply_deformation(image, coordinates):
        # ndimage expects uint8 otherwise introduces artifacts. Don't ask me why, its stupid.
        deformed = scipy.ndimage.map_coordinates(image, coordinates, mode='reflect')
        deformed = np.reshape(deformed, image.shape) 
        return deformed

    displacement_x = np.random.normal(size=images.shape[:2], scale=10)
    displacement_y = np.random.normal(size=images.shape[:2], scale=10)

    # smooth over image
    coords_x, coords_y = np.meshgrid(np.arange(0,images.shape[0]), np.arange(0,images.shape[1]), indexing='ij')

    displacement_x = coords_x.flatten() #+ scipy.ndimage.gaussian_filter(displacement_x, sigma=5).flatten()
    displacement_y = coords_y.flatten() #+ scipy.ndimage.gaussian_filter(displacement_y, sigma=5).flatten()
    
    coordinates = np.vstack([displacement_x, displacement_y])
    
    deformed = images.copy()
    for i in xrange(images.shape[2]):
        deformed[:,:,i] = apply_deformation(np.uint8(images[:,:,i]), coordinates)
    
    return deformed


def normalizeImage(img, saturation_level=0.05): #was 0.005
	sortedValues = np.sort( img.ravel())
	minVal = np.float32(sortedValues[np.int(len(sortedValues) * (saturation_level / 2))])
	maxVal = np.float32(sortedValues[np.int(len(sortedValues) * (1 - saturation_level / 2))])
	normImg = np.float32(img - minVal) * (255 / (maxVal-minVal))
	normImg[normImg<0] = 0
	normImg[normImg>255] = 255
	return (np.float32(normImg) / 255.0)
	
	
def generate_experiment_data_supervised(purpose='train', nsamples=1000, patchSize=29, balanceRate=0.5, rng=np.random):
    start_time = time.time()

    if os.path.exists('/media/vkaynig/Data1/Cmor_paper_data/'):
        pathPrefix = '/media/vkaynig/Data1/Cmor_paper_data/'
    else:
        pathPrefix = '/n/pfister_lab/vkaynig/'

    img_search_string_membraneImages = pathPrefix + 'labels/membranes_nonDilate/' + purpose + '/*.tif'
    img_search_string_backgroundMaskImages = pathPrefix + 'labels/background_nonDilate/' + purpose + '/*.tif'
	
    img_search_string_grayImages = pathPrefix + 'images/' + purpose + '/*.tif'
	
    img_files_gray = sorted( glob.glob( img_search_string_grayImages ) )
    img_files_label = sorted( glob.glob( img_search_string_membraneImages ) )
    img_files_backgroundMask = sorted( glob.glob( img_search_string_backgroundMaskImages ) )
	
    whole_set_patches = np.zeros((nsamples, patchSize*patchSize), dtype=np.float)
    whole_set_labels = np.zeros(nsamples, dtype=np.int32)
	
    #how many samples per image?
    nsamples_perImage = np.uint(np.ceil( 
		(nsamples) / np.float(np.shape(img_files_gray)[0])
	)) 
    print 'using ' + np.str(nsamples_perImage) + ' samples per image.'
    counter = 0
	
    img = mahotas.imread(img_files_gray[0])
    grayImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    labelImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    maskImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
	
    for img_index in xrange(np.shape(img_files_gray)[0]):
        img = mahotas.imread(img_files_gray[img_index])
        img = normalizeImage(img) 
        grayImages[:,:,img_index] = img
        label_img = mahotas.imread(img_files_label[img_index])        
        labelImages[:,:,img_index] = label_img
        mask_img = mahotas.imread(img_files_backgroundMask[img_index])
        maskImages[:,:,img_index] = mask_img
		
    for img_index in xrange(np.shape(img_files_gray)[0]):
        img = grayImages[:,:,img_index]        
        label_img = labelImages[:,:,img_index]
        mask_img = maskImages[:,:,img_index]
		
        #get rid of invalid image borders
        border_patch = np.int(np.ceil(patchSize/2.0))
        border = np.int(np.ceil(np.sqrt(2*(border_patch**2))))
        label_img[:border,:] = 0 #top
        label_img[-border:,:] = 0 #bottom
        label_img[:,:border] = 0 #left
        label_img[:,-border:] = 0 #right
		
        mask_img[:border,:] = 0
        mask_img[-border:,:] = 0
        mask_img[:,:border] = 0
        mask_img[:,-border:] = 0
		
        membrane_indices = np.nonzero(label_img)
        non_membrane_indices = np.nonzero(mask_img)
		
        positiveSample = True
        for i in xrange(nsamples_perImage):
            if counter >= nsamples:
                break
            if positiveSample:
                randmem = random.choice(xrange(len(membrane_indices[0])))
                (row,col) = (membrane_indices[0][randmem], 
                             membrane_indices[1][randmem])
                label = 1.0
                positiveSample = False
            else:
                randmem = random.choice(xrange(len(non_membrane_indices[0])))
                (row,col) = (non_membrane_indices[0][randmem], 
                             non_membrane_indices[1][randmem])
                label = 0.0
                positiveSample = True
				
            imgPatch = img[row-border+1:row+border, col-border+1:col+border]
            imgPatch = skimage.transform.rotate(imgPatch, random.choice(xrange(360)))
            imgPatch = imgPatch[border-border_patch:border+border_patch-1,border-border_patch:border+border_patch-1]

            if random.random() < 0.5:
                imgPatch = np.fliplr(imgPatch)
            imgPatch = np.rot90(imgPatch, random.randint(0,3))
                
            whole_set_patches[counter,:] = imgPatch.flatten()
            whole_set_labels[counter] = label
            counter += 1
            
    #normalize data
    whole_data = np.float32(whole_set_patches)
	
    whole_data = whole_data - 0.5
	
    data = whole_data.copy()
    labels = whole_set_labels.copy()
	
    #remove the sorting in image order
    shuffleIndex = rng.permutation(np.shape(labels)[0])
    for i in xrange(np.shape(labels)[0]):  
        whole_data[i,:] = data[shuffleIndex[i],:]
        whole_set_labels[i] = labels[shuffleIndex[i]]
		
    data_set = (whole_data, whole_set_labels)    
    
    end_time = time.time()
    total_time = (end_time - start_time)
    print 'Running time: ' + '%.2fm' % (total_time / 60.)
    rval = data_set
    return rval


def generate_image_data(img, patchSize=29, rows=1):
    img = normalizeImage(img) 

    # pad image borders
    border = np.int(np.ceil(patchSize/2.0))
    img_padded = np.pad(img, border, mode='reflect')

    whole_set_patches = np.zeros((len(rows)*img.shape[1], patchSize**2))

    counter = 0
    for row in rows:
        for col in xrange(img.shape[1]):
            imgPatch = img_padded[row+1:row+2*border, col+1:col+2*border]
            whole_set_patches[counter,:] = imgPatch.flatten()
            counter += 1

    #normalize data
    whole_set_patches = np.float32(whole_set_patches)
    whole_set_patches = whole_set_patches - 0.5

    return whole_set_patches


def stupid_map_wrapper(parameters):
        f = parameters[0]
        args = parameters[1:]
        return f(*args)


# changed the patch sampling to use upper left corner instead of middle pixel
# for patch labels it doesn't matter and it makes sampling even and odd patches easier
def generate_experiment_data_patch_prediction(purpose='train', nsamples=1000, patchSize=29, outPatchSize=1):
    def relabel(image):
        id_list = np.unique(image)
        for index, id in enumerate(id_list):
            image[image==id] = index
        return image

    start_time = time.time()

    if os.path.exists('/media/vkaynig/Data1/Cmor_paper_data/'):
        pathPrefix = '/media/vkaynig/Data1/Cmor_paper_data/'
    else:
        pathPrefix = '/n/pfister_lab/vkaynig/'

    img_search_string_membraneImages = pathPrefix + 'labels/membranes_fullContour/' + purpose + '/train*.tif'
    img_search_string_labelImages = pathPrefix + 'labels/' + purpose + '/train*.tif'
    img_search_string_grayImages = pathPrefix + 'images/' + purpose + '/train*.tif'

    img_files_gray = sorted( glob.glob( img_search_string_grayImages ) )
    img_files_membrane = sorted( glob.glob( img_search_string_membraneImages ) )
    img_files_labels = sorted( glob.glob( img_search_string_labelImages ) )

    whole_set_patches = np.zeros((nsamples, patchSize**2), dtype=np.float)
    whole_set_labels = np.zeros((nsamples, outPatchSize**2), dtype=np.int32)
    whole_set_membranes = np.zeros((nsamples, outPatchSize**2), dtype=np.int32)

    #how many samples per image?
    nsamples_perImage = np.uint(np.ceil( 
            (nsamples) / np.float(np.shape(img_files_gray)[0])
            )) 
    print 'using ' + np.str(nsamples_perImage) + ' samples per image.'
    counter = 0

    img = mahotas.imread(img_files_gray[0])
    grayImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    labelImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    membraneImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    maskImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))

    # read the data
    # in random order
    read_order = np.random.permutation(np.shape(img_files_gray)[0])
    for img_index in read_order:
        #print img_files_gray[img_index]
        img = mahotas.imread(img_files_gray[img_index])
        # normalizes [0,1]
        img = normalizeImage(img) 
        grayImages[:,:,img_index] = img
        membrane_img = mahotas.imread(img_files_membrane[img_index])/255.        
        membraneImages[:,:,img_index] = membrane_img
        maskImages[:,:,img_index] = 1.0
        if purpose == 'validate':
            label_img = mahotas.imread(img_files_labels[img_index])        
            label_img = np.double(label_img)
            labelImages[:,:,img_index] = label_img
            
    for img_index in xrange(np.shape(img_files_gray)[0]):
        #print img_files_gray[read_order[img_index]]
        img = grayImages[:,:,img_index]        
        label_img = labelImages[:,:,img_index]
        membrane_img = membraneImages[:,:,img_index]
        mask_img = maskImages[:,:,img_index]

        if purpose=='train':
           membrane_img = adjust_imprecise_boundaries(img, membrane_img, 1)

        #get rid of invalid image borders
        mask_img[:,-patchSize:] = 0
        mask_img[-patchSize:,:] = 0

        valid_indices = np.nonzero(mask_img)

        for i in xrange(nsamples_perImage):
            
            if counter >= nsamples:
                break

            randmem = random.choice(xrange(len(valid_indices[0])))
            (row,col) = (valid_indices[0][randmem], 
                         valid_indices[1][randmem])

            imgPatch = img[row:row+patchSize, col:col+patchSize]
            membranePatch = membrane_img[row:row+patchSize, col:col+patchSize]
            labelPatch = label_img[row:row+patchSize, col:col+patchSize]

            if random.random() < 0.5:
                imgPatch = np.fliplr(imgPatch)
                membranePatch = np.fliplr(membranePatch)
                if purpose == 'validate':
                    labelPatch = np.fliplr(labelPatch)

            rotateInt = random.randint(0,3)
            imgPatch = np.rot90(imgPatch, rotateInt)
            membranePatch = np.rot90(membranePatch, rotateInt)
            if purpose=='validate':
                labelPatch = np.rot90(labelPatch, rotateInt)

            if purpose=='validate':
                labelPatch = relabel(labelPatch)
                imgPatch, membranePatch, labelPatch = deform_images(imgPatch, membranePatch, np.uint8(labelPatch))
            else:
                imgPatch, membranePatch = deform_images(imgPatch, membranePatch)
            
            imgPatch = imgPatch / np.double(np.max(imgPatch))
            membranePatch = membranePatch / np.double(np.max(membranePatch))

            # crop labelPatch to potentially smaller output size
            offset_small_patch = int(np.ceil((patchSize - outPatchSize) / 2.0))
            membranePatch = membranePatch[offset_small_patch:offset_small_patch+outPatchSize, 
                                    offset_small_patch:offset_small_patch+outPatchSize]
            labelPatch = labelPatch[offset_small_patch:offset_small_patch+outPatchSize, 
                                    offset_small_patch:offset_small_patch+outPatchSize]

            whole_set_patches[counter,:] = imgPatch.flatten()
            whole_set_labels[counter] = labelPatch.flatten()
            whole_set_membranes[counter] = np.int32(membranePatch.flatten() > 0)
            counter += 1

    #normalize data
    whole_data = np.float32(whole_set_patches)
    whole_data = whole_data - 0.5

    data = whole_data.copy()
    labels = whole_set_labels.copy()
    membranes = whole_set_membranes.copy()

    #remove the sorting in image order
    shuffleIndex = np.random.permutation(np.shape(membranes)[0])
    for i in xrange(np.shape(membranes)[0]):  
        whole_data[i,:] = data[shuffleIndex[i],:]
        whole_set_labels[i,:] = labels[shuffleIndex[i],:]
        whole_set_membranes[i,:] = membranes[shuffleIndex[i],:]
    
    if purpose == 'validate':
        data_set = (whole_data, whole_set_membranes, whole_set_labels)    
    else:
        data_set = (whole_data, whole_set_membranes)    

    end_time = time.time()
    total_time = (end_time - start_time)
    print 'Running time: ', total_time / 60.
    print 'finished sampling data'

    return data_set



def generate_experiment_data_patch_prediction_layers(purpose='train', nsamples=1000, patchSize=29, outPatchSize=1, nr_layers=3):
    def relabel(image):
        id_list = np.unique(image)
        for index, id in enumerate(id_list):
            image[image==id] = index
        return image

    start_time = time.time()

    if os.path.exists('/media/vkaynig/Data1/Cmor_paper_data/'):
        pathPrefix = '/media/vkaynig/Data1/Cmor_paper_data/'
    else:
        pathPrefix = '/n/pfister_lab/vkaynig/'

    img_search_string_membraneImages = pathPrefix + 'labels/membranes_fullContour/' + purpose + '/*.tif'
    img_search_string_labelImages = pathPrefix + 'labels/' + purpose + '/*.tif'
    img_search_string_grayImages = pathPrefix + 'images/' + purpose + '/*.tif'

    img_files_gray = sorted( glob.glob( img_search_string_grayImages ) )
    img_files_membrane = sorted( glob.glob( img_search_string_membraneImages ) )
    img_files_labels = sorted( glob.glob( img_search_string_labelImages ) )

    whole_set_patches = np.zeros((nsamples, nr_layers, patchSize**2), dtype=np.float)
    whole_set_labels = np.zeros((nsamples, outPatchSize**2), dtype=np.int32)
    whole_set_membranes = np.zeros((nsamples, outPatchSize**2), dtype=np.int32)

    #how many samples per image?
    nsamples_perImage = np.uint(np.ceil( 
            (nsamples) / np.float(np.shape(img_files_gray)[0])
            )) 
    print 'using ' + np.str(nsamples_perImage) + ' samples per image.'
    counter = 0

    img = mahotas.imread(img_files_gray[0])
    grayImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    labelImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    membraneImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))
    maskImages = np.zeros((img.shape[0],img.shape[1], np.shape(img_files_gray)[0]))

    # read the data
    # in random order
    #read_order = np.random.permutation(np.shape(img_files_gray)[0])
    for img_index in range(np.shape(img_files_gray)[0]):
        #print img_files_gray[img_index]
        img = mahotas.imread(img_files_gray[img_index])
        # normalizes [0,1]
        img = normalizeImage(img) 
        grayImages[:,:,img_index] = img
        membrane_img = mahotas.imread(img_files_membrane[img_index])/255.        
        membraneImages[:,:,img_index] = membrane_img
        maskImages[:,:,img_index] = 1.0
        if purpose == 'validate':
            label_img = mahotas.imread(img_files_labels[img_index])        
            label_img = np.double(label_img)
            labelImages[:,:,img_index] = label_img
            
    for img_index in xrange(np.shape(img_files_gray)[0]):
        img_cs = int(np.floor(nr_layers/2))
        img_valid_range_indices = np.clip(range(img_index-img_cs,img_index+img_cs+1),0,np.shape(img_files_gray)[0]-1)
        img = grayImages[:,:,img_valid_range_indices]     
        label_img = labelImages[:,:,img_index]
        membrane_img = membraneImages[:,:,img_index]
        mask_img = maskImages[:,:,img_index]

        if purpose=='train':
            # adjust according to middle image
            membrane_img = adjust_imprecise_boundaries(img[:,:,img_cs], membrane_img, 0)

        #get rid of invalid image borders
        mask_img[:,-patchSize:] = 0
        mask_img[-patchSize:,:] = 0

        valid_indices = np.nonzero(mask_img)

        for i in xrange(nsamples_perImage):
            
            if counter >= nsamples:
                break

            randmem = random.choice(xrange(len(valid_indices[0])))
            (row,col) = (valid_indices[0][randmem], 
                         valid_indices[1][randmem])

            imgPatch = img[row:row+patchSize, col:col+patchSize,:]
            membranePatch = membrane_img[row:row+patchSize, col:col+patchSize]
            labelPatch = label_img[row:row+patchSize, col:col+patchSize]

            if random.random() < 0.5:
                for flip_i in xrange(nr_layers):
                    imgPatch[:,:,flip_i] = np.fliplr(imgPatch[:,:,flip_i])
                membranePatch = np.fliplr(membranePatch)
                if purpose == 'validate':
                    labelPatch = np.fliplr(labelPatch)

            rotateInt = random.randint(0,3)
            for rot_i in xrange(nr_layers):
                imgPatch[:,:,rot_i] = np.rot90(imgPatch[:,:,rot_i], rotateInt)
            membranePatch = np.rot90(membranePatch, rotateInt)
            if purpose=='validate':
                labelPatch = np.rot90(labelPatch, rotateInt)

            if purpose=='validate':
                labelPatch = relabel(labelPatch)
                deformed_images = deform_images_list(np.dstack([imgPatch*255, np.reshape(membranePatch*255,(patchSize,patchSize,1)), np.uint8(np.reshape(labelPatch,(patchSize,patchSize,1)))]))
                imgPatch, membranePatch, labelPatch = np.split(deformed_images,[imgPatch.shape[2],imgPatch.shape[2]+1], axis=2)
            else:
                deformed_images = deform_images_list(np.dstack([imgPatch*255, np.reshape(membranePatch,(patchSize,patchSize,1))*255]))
                imgPatch, membranePatch = np.split(deformed_images,[imgPatch.shape[2]], axis=2)            

            imgPatch = imgPatch / np.double(np.max(imgPatch))
            membranePatch = membranePatch / np.double(np.max(membranePatch))

            # crop labelPatch to potentially smaller output size
            offset_small_patch = int(np.ceil((patchSize - outPatchSize) / 2.0))
            membranePatch = membranePatch[offset_small_patch:offset_small_patch+outPatchSize, 
                                    offset_small_patch:offset_small_patch+outPatchSize]
            labelPatch = labelPatch[offset_small_patch:offset_small_patch+outPatchSize, 
                                    offset_small_patch:offset_small_patch+outPatchSize]

            #whole_set_patches = np.zeros((nsamples, nr_layers, patchSize**2), dtype=np.float)
            for patch_i in xrange(nr_layers):
                whole_set_patches[counter,patch_i,:] = imgPatch[:,:,patch_i].flatten()
            whole_set_labels[counter] = labelPatch.flatten()
            whole_set_membranes[counter] = np.int32(membranePatch.flatten() > 0)
            counter += 1

    #normalize data
    whole_data = np.float32(whole_set_patches)
    whole_data = whole_data - 0.5

    data = whole_data.copy()
    labels = whole_set_labels.copy()
    membranes = whole_set_membranes.copy()

    #remove the sorting in image order
    shuffleIndex = np.random.permutation(np.shape(membranes)[0])
    for i in xrange(np.shape(membranes)[0]):  
        whole_data[i,:,:] = data[shuffleIndex[i],:,:]
        whole_set_labels[i,:] = labels[shuffleIndex[i],:]
        whole_set_membranes[i,:] = membranes[shuffleIndex[i],:]
    
    if purpose == 'validate':
        data_set = (whole_data, whole_set_membranes, whole_set_labels)    
    else:
        data_set = (whole_data, whole_set_membranes)    

    end_time = time.time()
    total_time = (end_time - start_time)
    print 'Running time: ', total_time / 60.
    print 'finished sampling data'

    return data_set

if __name__=="__main__":
    import uuid

    test = generate_experiment_data_patch_prediction(purpose='train', nsamples=30, patchSize=572, outPatchSize=388)
    dir_path = './training_patches/'
    
    for i in xrange(30):
        unique_filename = str(uuid.uuid4())
        img = np.reshape(test[1][i],(388,388))
        img_gray = np.reshape(test[0][i],(572,572))
        mahotas.imsave(dir_path+unique_filename+'.tif', np.uint8(img*255))
        mahotas.imsave(dir_path+unique_filename+'_gray.tif', np.uint8((img_gray+0.5)*255))
        

    #data_val = generate_experiment_data_supervised(purpose='validate', nsamples=10000, patchSize=65, balanceRate=0.5)
    #data = generate_experiment_data_patch_prediction(purpose='validate', nsamples=2, patchSize=315, outPatchSize=215)
    # plt.imshow(np.reshape(data[0][0],(315,315))); plt.figure()
    # plt.imshow(np.reshape(data[1][0],(215,215))); plt.figure()
    # plt.imshow(np.reshape(data[2][0],(215,215))); plt.show()

    # image = mahotas.imread('ac3_input_0141.tif')
    # image = normalizeImage(image)
    # label = mahotas.imread('ac3_labels_0141.tif') / 255.
    # test = adjust_imprecise_boundaries(image, label, 10)

    # plt.imshow(label+image); plt.show()
    # plt.imshow(test+image); plt.show()
