#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python version: 3.6
# 这个用于CNN的不同分布差异数据仿真, 手写体只需要一个通道
import matplotlib
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import copy
import numpy as np
from torchvision import datasets, transforms
import torch
import math

from utils.sampling import mnist_iid, mnist_noniid, cifar_iid
from utils.options import args_parser
from models.Update import LocalUpdate
from models.Update import CLUpdate
from models.Nets import MLP, CNNMnist, CNNCifar
from models.Fed import FedAvg
from models.Fed import FedAvg_Optimize
from models.test import test_img

if __name__ == '__main__':
    # parse args
    args = args_parser()
    args.device = torch.device('cuda:{}'.format(args.gpu) if torch.cuda.is_available() and args.gpu != -1 else 'cpu')

    # load dataset and split users
    trans_mnist = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
    dataset_train = datasets.MNIST('../data/mnist/', train=True, download=False, transform=trans_mnist)
    dataset_test = datasets.MNIST('../data/mnist/', train=False, download=False, transform=trans_mnist)

    # sample users

    num_img = [1000, 600, 600, 400, 400]
    num_label = [2, 1, 3, 2, 8]
    Ld = [0.0612, 0.0335, 0.2008, 0.0582, 0.6465]

    num_img = [1000, 600, 600, 400, 400]
    num_label = [1, 1, 1, 1, 8]
    Ld_L = [0.0346 ,   0.0979 ,   0.0723 ,   0.0766 ,   0.7186]

    dict_users, dict_users_L = {}, {}
    for k in range(len(num_img)):
        #  导入unbalance数据集
        csv_path_train_data = 'csv/' + 'user' + str(k) + 'train_index' + '_unbalance' + '.csv'
        train_index = pd.read_csv(csv_path_train_data, header=None)

        # 修剪数据集使得只有图片和标签,把序号剔除
        train_index = train_index.values
        train_index = train_index.T
        dict_users[k] = np.array(train_index[0].astype(int))

        #  导入balance数据集
        csv_path_train_data = 'csv/' + 'user' + str(k) + 'train_index' + '_balance' + '.csv'
        train_index = pd.read_csv(csv_path_train_data, header=None)

        train_index = train_index.values
        train_index = train_index.T
        dict_users_L[k] = np.array(train_index[0].astype(int))

    dict_users_iid_temp = mnist_iid(dataset_train, args.num_users)
    dict_users_iid = []
    for iter in range(args.num_users):
        dict_users_iid.extend(dict_users_iid_temp[iter])

    img_size = dataset_train[0][0].shape
    # print('img_size=',img_size)

    net_glob = CNNMnist(args=args).to(args.device)

    net_glob_cl_iid = copy.deepcopy(net_glob)
    net_glob_fl = copy.deepcopy(net_glob)
    net_glob_cl = copy.deepcopy(net_glob)
    net_glob_fl2 = copy.deepcopy(net_glob)
    net_glob_cl2 = copy.deepcopy(net_glob)

    net_glob_cl_iid.train()
    net_glob_fl.train()
    net_glob_cl.train()
    net_glob_fl2.train()
    net_glob_cl2.train()

    # copy weights
    w_glob_cl_iid = net_glob_cl_iid.state_dict()
    w_glob_fl = net_glob_fl.state_dict()
    w_glob_cl = net_glob_cl.state_dict()
    w_glob_fl2 = net_glob_fl2.state_dict()
    w_glob_cl2 = net_glob_cl2.state_dict()

    acc_train_cl_his, acc_train_fl_his, acc_train_cl_his_iid = [], [], []
    acc_train_cl_his2, acc_train_fl_his2 = [], []

    # 新建存放数据的文件
    filename = 'result/CNN_D/' + "Accuracy_FedAvg_idd_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Accuracy_FedAvg_S_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Accuracy_FedAvg_Optimize_S_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Accuracy_FedAvg_L_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Accuracy_FedAvg_Optimize_L_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Loss_FedAvg_S_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Loss_FedAvg_Optimize_S_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Loss_FedAvg_L_CNN.csv"
    np.savetxt(filename, [])
    filename = 'result/CNN_D/' + "Loss_FedAvg_Optimize_L_CNN.csv"
    np.savetxt(filename, [])

    for iter in range(args.epochs):  # num of iterations
        # CL setting

        # testing
        net_glob_cl_iid.eval()
        acc_test_cl, loss_test_clxx = test_img(net_glob_cl_iid, dataset_test, args)
        print("Testing accuracy: {:.2f}".format(acc_test_cl))
        acc_train_cl_his_iid.append(acc_test_cl)

        filename = 'result/CNN_D/' + "Accuracy_FedAvg_idd_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(acc_test_cl) + ',')

        glob_cl = CLUpdate(args=args, dataset=dataset_train, idxs=dict_users_iid)
        w_cl, loss_cl = glob_cl.cltrain(net=copy.deepcopy(net_glob_cl_iid).to(args.device))
        net_glob_cl_iid.load_state_dict(w_cl)

        # Loss
        print('cl,iter = ', iter, 'loss=', loss_cl)
        filename = 'result/CNN_D/' + "Loss_FedAvg_idd_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(loss_cl) + ',')

        # FL setting

        # testing
        net_glob_fl.eval()
        acc_test_fl, loss_test_flxx = test_img(net_glob_fl, dataset_test, args)
        print("Testing accuracy: {:.2f}".format(acc_test_fl))
        acc_train_fl_his.append(acc_test_fl)

        filename = 'result/CNN_D/' + "Accuracy_FedAvg_S_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(acc_test_fl) + ',')

        w_locals, loss_locals = [], []
        # M clients local update
        m = max(int(args.frac * args.num_users), 1)  # num of selected users
        idxs_users = np.random.choice(range(args.num_users), m, replace=False)  # select randomly m clients
        for idx in idxs_users:
            local = LocalUpdate(args=args, dataset=dataset_train, idxs=dict_users[idx])  # data select
            w, loss = local.train(net=copy.deepcopy(net_glob_fl).to(args.device))
            w_locals.append(copy.deepcopy(w))  # collect local model
            loss_locals.append(copy.deepcopy(loss))  # collect local loss fucntion

        w_glob_fl = FedAvg(w_locals)  # update the global model
        net_glob_fl.load_state_dict(w_glob_fl)  # copy weight to net_glob

        # Loss
        loss = sum(loss_locals) / len(loss_locals)
        print('fl,iter = ', iter, 'loss=', loss)
        filename = 'result/CNN_D/' + "Loss_FedAvg_S_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(loss) + ',')

        # FL_Optimize setting

        # testing
        net_glob_cl.eval()
        acc_test_cl, loss_test_clxx = test_img(net_glob_cl, dataset_test, args)
        print("Testing accuracy: {:.2f}".format(acc_test_cl))
        acc_train_cl_his.append(acc_test_cl)

        filename = 'result/CNN_D/' + "Accuracy_FedAvg_Optimize_S_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(acc_test_cl) + ',')

        w_locals, loss_locals = [], []
        # M clients local update
        for idx in range(args.num_users):
            local = LocalUpdate(args=args, dataset=dataset_train, idxs=dict_users[idx])  # data select
            w, loss = local.train(net=copy.deepcopy(net_glob_cl).to(args.device))
            w_locals.append(copy.deepcopy(w))  # collect local model
            loss_locals.append(copy.deepcopy(loss))  # collect local loss fucntion

        w_glob_cl = FedAvg_Optimize(w_locals, Ld)  # update the global model
        net_glob_cl.load_state_dict(w_glob_cl)  # copy weight to net_glob

        loss = sum(loss_locals) / len(loss_locals)
        print('fl_OP,iter = ', iter, 'loss=', loss)

        filename = 'result/CNN_D/' + "Loss_FedAvg_Optimize_S_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(loss) + ',')

        # FL_biggdiff setting

        # testing
        net_glob_fl2.eval()
        acc_test_fl2, loss_test_flxx = test_img(net_glob_fl2, dataset_test, args)
        print("Testing accuracy: {:.2f}".format(acc_test_fl2))
        acc_train_fl_his2.append(acc_test_fl2)

        filename = 'result/CNN_D/' + "Accuracy_FedAvg_L_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(acc_test_fl2) + ',')

        w_locals, loss_locals = [], []
        # M clients local update
        m = max(int(args.frac * args.num_users), 1)  # num of selected users
        idxs_users = np.random.choice(range(args.num_users), m, replace=False)  # select randomly m clients
        for idx in idxs_users:
            local = LocalUpdate(args=args, dataset=dataset_train, idxs=dict_users_L[idx])  # data select
            w, loss = local.train(net=copy.deepcopy(net_glob_fl2).to(args.device))
            w_locals.append(copy.deepcopy(w))  # collect local model
            loss_locals.append(copy.deepcopy(loss))  # collect local loss fucntion

        w_glob_fl2 = FedAvg(w_locals)  # update the global model
        net_glob_fl2.load_state_dict(w_glob_fl2)  # copy weight to net_glob

        # Loss
        loss = sum(loss_locals) / len(loss_locals)
        print('fl_L,iter = ', iter, 'loss=', loss)
        filename = 'result/CNN_D/' + "Loss_FedAvg_L_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(loss) + ',')

        # FL_Optimize_L setting
        # testing
        net_glob_cl2.eval()
        acc_test_cl2, loss_test_clxx = test_img(net_glob_cl2, dataset_test, args)
        print("Testing accuracy: {:.2f}".format(acc_test_cl2))
        acc_train_cl_his2.append(acc_test_cl2)

        filename = 'result/CNN_D/' + "Accuracy_FedAvg_Optimize_L_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(acc_test_cl2) + ',')

        w_locals, loss_locals = [], []
        # M clients local update
        for idx in range(args.num_users):
            local = LocalUpdate(args=args, dataset=dataset_train, idxs=dict_users_L[idx])  # data select
            w, loss = local.train(net=copy.deepcopy(net_glob_cl2).to(args.device))
            w_locals.append(copy.deepcopy(w))  # collect local model
            loss_locals.append(copy.deepcopy(loss))  # collect local loss fucntion

        w_glob_cl2 = FedAvg_Optimize(w_locals, Ld_L)  # update the global model
        net_glob_cl2.load_state_dict(w_glob_cl2)  # copy weight to net_glob

        loss = sum(loss_locals) / len(loss_locals)
        print('fl_OP_L,iter = ', iter, 'loss=', loss)

        filename = 'result/CNN_D/' + "Loss_FedAvg_Optimize_L_CNN.csv"
        with open(filename, "a") as myfile:
            myfile.write(str(loss) + ',')

    colors = ["navy", "red", "black", "orange", "violet"]
    labels = ["FedAvg_S", "FedAvg_Optimize_S", "FedAvg_L", "FedAvg_Optimize_L", "CL_iid"]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(acc_train_fl_his, c=colors[0], label=labels[0])
    ax.plot(acc_train_cl_his, c=colors[1], label=labels[1])
    ax.plot(acc_train_fl_his2, c=colors[2], label=labels[2])
    ax.plot(acc_train_cl_his2, c=colors[3], label=labels[3])
    ax.plot(acc_train_cl_his_iid, c=colors[4], label=labels[4])
    ax.legend()
    plt.xlabel('Iterations')
    plt.ylabel('Accuracy')
    plt.savefig('Figure/Accuracy_CNN.png')
