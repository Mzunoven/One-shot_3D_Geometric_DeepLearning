import numpy as np
#import pandas as pd
import matplotlib.pyplot as plt
#from rdkit import Chem
import torch
import torch.nn.functional as F
from torch import nn
from torch.nn import Linear
#from torch_geometric.data import Data
#from torch_geometric.data import DataLoader
from torch.utils.data import DataLoader
#import torch_geometric.nn as GCN
from torch.optim import Adam

from models import CNN
from models import GNN
from voxDataset import trainData
from voxDataset import testData
import scipy.io

IntType = np.int64


def getData(batch_dim):

    # ModelNet10 provides a dataset of models in the form of .OFF files. A voxelized form of the dataset was provided by http://aguo.us/writings/classify-modelnet.html.
    dataset = np.load('modelnet10.npz')
    # print(dataset.files)

    xTest = dataset['X_test']  # ndarray of size (908, 30, 30, 30)
    xTrain = dataset['X_train']  # ndarray of size (3991, 30, 30, 30)
    yTest = dataset['y_test']  # ndarray of size (908, )
    yTrain = dataset['y_train']  # ndarray of size (3991, )

    # y labels are ints ranging from 0 to 9, indicating classification as one of the models in the modelnet10 framework.
    # x arrays are 30x30x30 binary grids of either 0s or 1s, indicating the presence of a voxel in that given space.
    # Each voxel could be contained in a 24x24x24 cube. The additional space serves as padding.

    xTrain_loader = DataLoader(xTrain, batch_size=batch_dim, shuffle=True)
    yTrain_loader = DataLoader(yTrain, batch_size=batch_dim, shuffle=True)

    return xTrain_loader, yTrain_loader


def one_hot_encoding(labels, num_class=None):
    """one_hot_encoding Create One-Hot Encoding for labels

    Arguments:
        labels {np.ndarray or list} -- The original labels

    Keyword Arguments:
        num_class {int} -- Number of classses. If None, automatically 
            compute the number of calsses in the given labels (default: {None})

    Returns:
        np.ndarray -- One-hot encoded version of labels
    """

    if num_class is None:
        num_class = np.max(labels) + 1
    one_hot_labels = np.zeros((len(labels), num_class))
    one_hot_labels[np.arange(len(labels)), labels] = 1
    return one_hot_labels.astype(IntType)


def main():
    # Set device
    device = 'cpu'

    # Set hyperparameters
    batch_dim = 64
    lr = 0.05
    GNN_epochs = 100
    CNN_epochs = 3
    latent_dim = 64

    # Load data
    #x_loader = getData(batch_dim)
    #y_loader = getData(batch_dim)
    trainDataSet = trainData()
    trainLoader = DataLoader(dataset=trainDataSet,
                             batch_size=batch_dim, shuffle=True, num_workers=0)
    testDataSet = testData()
    testLoader = DataLoader(dataset=testDataSet,
                            batch_size=batch_dim, shuffle=True, num_workers=0)
    # Semantic Embeddings
    set_idx = np.int16([1, 2, 8, 12, 14, 22, 23, 30, 33, 35])
    glovevector = scipy.io.loadmat('../data/ModelNet40_glove')
    glove_set = glovevector['word']
    glove = glove_set[set_idx, :]  # Is a 10 x 300 ndarray
    # print(type(glove))
    # print(glove)
    # print(glove.shape)

    # We must first use a pre-trained CNN to obtain data to be used for the GCN and semantic embeddings.
    # The paper we are referencing supports the use of 'res50' or 'inception' networks. However, these are for 2d images.
    # We will instead be using the voxnet network to classify our voxel models, obtained from: https://github.com/dimatura/voxnet.
    #   **pytorch version supposedly provided here https://github.com/lxxue/voxnet-pytorch
    # Then use a GCN (input: word embeddings for every object class, output: visual classifier for every object class)

    # No easily usable pre-trained voxel CNN. We'll have to make our own.

    # CNN---------------------------------------------------------------------------------------------------------------------

    # Build Model
    voxCNN = CNN(batch_dim).to(device)

    # Define Loss Function
    loss_func = nn.CrossEntropyLoss()
    #loss_func = nn.BCELoss()
    loss_glove = nn.MSELoss()

    # Optimizer
    optim = Adam(voxCNN.parameters(), lr=lr)

    # for name, param in voxCNN.named_parameters():
    #    if param.requires_grad:
    #        print(name, param.data.dtype)

    # Train CNN

    epochVals = []
    lossVals = []

    #print("BEGIN TRAINING")

    for epoch in range(CNN_epochs):
        for num_batch, (x_batch, labels) in enumerate(trainLoader):

            # x_batch is of dim batch_size, x, y, z
            # labels is of dim batch_size
            # unsqueeze to make it batch_size, numchannels, x, y, z

            # print(labels.shape) #glovedata is of shape batchsize x 300

            x_batch = torch.unsqueeze(x_batch, 1)
            x_batch, labels = x_batch.to(device), labels.to(device)
            x_batch = x_batch.float()
            # labels = one_hot_encoding(labels)
            #labels = labels.long()

            # print(x_batch.shape)
            # print(labels.shape)

            # should return a (batch_size, ) tensor to compare w/ labels
            CNN_pred = voxCNN(x_batch)

            # print(CNN_pred.shape)
            # print(labels.shape)

            # print(labels)

            # print(CNN_pred.dtype)
            # print(labels.dtype)
            # print(CNN_pred[0])

            #loss = loss_func(CNN_pred, labels)

            labels = labels.float()

            loss = loss_glove(CNN_pred, labels)

            # print(loss)
            optim.zero_grad()
            loss.backward()
            optim.step()
            # break

            # print("Batch ", num_batch)
            if (num_batch + 1) % 20 == 0:
                # print(CNN_pred)
                print("Epoch: [{}/{}], Batch: {}, Loss: {}".format(epoch +
                                                                   1, CNN_epochs, num_batch+1, loss.item()))
            epochVals = epochVals + [num_batch + 63*epoch]
            lossVals = lossVals + [loss.item()]
        # break

    #print("FINISH TRAINING")

    plt.figure()
    for i in range(len(epochVals)):
        plt.plot(epochVals, lossVals)
    plt.xlabel('Epoch')
    plt.ylabel('Losses')
    plt.show()

    # Test the Model

    # test_error = 0
    # voxCNN.eval()

    # x_pred = torch.empty(batch_dim)
    # y_labels = torch.empty(batch_dim)

    # with torch.no_grad():
    #     total = 0
    #     correct = 0
    #     for n_batch, (x_batch, labels) in enumerate(testLoader):
    #         x_batch, labels = x_batch.to(device), labels.to(device)
    #         x_batch = torch.unsqueeze(x_batch, 1)

    #         x_batch = x_batch.float()
    #         labels = labels.float() #Comment out when not using glove

    #         pred = voxCNN(x_batch)
    #         _, predicted = torch.max(pred.data, 1)

    #         total += labels.size(0)
    #         correct += (predicted == labels).sum().item()

    #         x_pred = torch.cat((x_pred, predicted.float()), 0)
    #         y_labels = torch.cat((y_labels, labels.float()), 0)

    #         # print(n_batch)

    #         test_error += loss_func(pred, labels).item()
    #         # break

    # print("Test Error:", test_error)
    # print("Test Accuracy: {} %".format(100 * correct / total))

    # Test model with Glove Data

    print("BEGIN TESTING")

    test_error = 0
    voxCNN.eval()

    batch_pred = torch.empty(batch_dim)
    x_pred = torch.empty(batch_dim)
    y_labels = torch.empty(batch_dim)
    temp_labels = torch.empty(batch_dim)

    glove = torch.from_numpy(testDataSet.get_glove_set())

    with torch.no_grad():
        total = 0
        correct = 0
        for n_batch, (x_batch, labels, true_label) in enumerate(testLoader):
            x_batch, labels = x_batch.to(device), labels.to(device)
            x_batch = torch.unsqueeze(x_batch, 1)
            # print(true_label.shape)

            x_batch = x_batch.float()  # batchsize x 30x30x30
            # labels = labels.float()  # batchsize x 300

            output = voxCNN(x_batch)  # batchsize x 300
            # output = torch.from_numpy(np.dot(output, glove.T))
            # print(output.shape)
            # print(labels.shape)

            batch_pred = torch.empty(output.size(0))
            # print(batch_pred.shape)
            temp_labels = torch.empty(batch_dim)

            for j in range(output.size(0)):
                minloss = 100000
                for i in range(10):
                    currentLabel = glove[i]  # should be size 300 tensor
                    # temp_labels[j] = i
                    loss = loss_glove(output[j], currentLabel)
                    if loss == 0:
                        temp_labels[j] = i
                    if loss < minloss:
                        minloss = loss
                        batch_pred[j] = i
                # if minloss < 0.005:
                #     correct = correct + 1

            # batch_pred = torch.unsqueeze(batch_pred, 1)

            # print(batch_pred)

            # batch_pred should now be of size batch_size x 1, with the highest likelihood label for each model

            _, predicted = torch.max(output.data, 1)

            predicted = torch.unsqueeze(predicted, 1)

            # print(predicted.shape)

            total += labels.size(0)
            correct += (batch_pred == true_label).sum().item()

            x_pred = torch.cat((x_pred, batch_pred.float()), 0)
            y_labels = torch.cat((y_labels, true_label.float()), 0)

            # print(x_pred.shape)
            # print(y_labels.shape)

            # print(n_batch)

            test_error += loss_glove(output, labels).item()
            # break

    print("Test Error:", test_error)
    print("Test Accuracy: {} %".format(100 * correct / total))
    # 10.90308370044053 %

    # Plot Predictions vs. Labels

    x_pred = torch.unsqueeze(x_pred, 1)
    y_labels = torch.unsqueeze(y_labels, 1)

    # print(x_pred)

    # xydata = torch.cat((x_pred, y_labels), 1)

    sortedlabels, indices = torch.sort(y_labels, 0)

    indices = torch.squeeze(indices)

    # print(indices.shape)

    sortedX = torch.index_select(x_pred, 0, indices)

    # sortedxy, indices = torch.sort(xydata, 0) #Sorts by label

    #xy = sortedxy.detach().numpy()

    # print(sortedX.shape)

    # Labels near the beginning and end are often wildly off
    # Should only be of size 908, due to batch_size interference somewhere the size becomes 928

    plt.figure()
    plt.plot(range(sortedX.shape[0]), sortedX[:, 0], 'r.')  # pred
    plt.plot(range(sortedlabels.shape[0]), sortedlabels[:], 'b.')  # labels
    plt.xlim(-1, 950)
    plt.ylim(-2, 12)
    plt.xlabel('Models')
    plt.ylabel('Object Class')
    plt.show()

    return 0


if __name__ == "__main__":
    main()
