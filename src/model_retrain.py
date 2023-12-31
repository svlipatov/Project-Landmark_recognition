import os
import torch
import random
import numpy as np
import torchvision
import matplotlib.pyplot as plt
import torchvision.transforms as transforms
import shutil
import time
import xml.etree.ElementTree as et
import pickle

from tqdm import tqdm
from PIL import Image
from torchvision import models
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
BATCH_SIZE = 32

use_gpu = torch.cuda.is_available()
device = 'cuda' if use_gpu else 'cpu'
print('Connected device:', device)

musk = 'https://drive.google.com/uc?export=download&id=1BOuq35QzO1YtKQkYGfj_vtBj3Ps5xyBN'
gates ='https://drive.google.com/uc?export=download&id=1jgHQF_NMpH9uMTvic9rGnURu_8UOGdiz'
bezos = 'https://drive.google.com/uc?export=download&id=1n5UaLL-TAkjIeBbTNcn-Czkp_A3Eslhj'
zuker = 'https://drive.google.com/uc?export=download&id=1ncPmYTg6EPHlUFdcjl_bXTbtWRLv2DXy'
jobs = 'https://drive.google.com/uc?export=download&id=1TX3hiRyvSYiYVZUFrbAhN3Jpp9cd0Q9s'


# Метки
face_lst=[
    ["Bill Gates",'people/gates500.jpg'],
    ["Jeff Besoz",'people/bezos500.jpg'],
    ["Mark Zuckerberg", 'people/zuckerberg500.jpg'],
    ["Steve Jobs",'people/jobs500.jpg']
]

# Датасет скачивается во время выполнения программы
import wget
from zipfile import ZipFile

# os.mkdir('data')

# url = 'https://drive.google.com/uc?export=download&id=120xqh0mYtYZ1Qh7vr-XFzjPbSKivLJjA'
# file_name = wget.download(url, 'data/')
#
# with ZipFile(file_name, 'r') as zip_file:
#     zip_file.extractall()
#
# link_lst = [musk, gates, bezos, zuker, jobs]
# for link in link_lst:
#     wget.download(link, 'data/')

# Датасет для тренировки
train_dataset = ImageFolder(
    root='people/train'
)
# Датасет для проверки
valid_dataset = ImageFolder(
    root='people/valid'
)

# augmentations (ухудшение качество чтобы не было переобучения)
normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
train_dataset.transform = transforms.Compose([
    transforms.Resize([70, 70]),
    transforms.RandomHorizontalFlip(),
    transforms.RandomAutocontrast(),
    transforms.RandomEqualize(),
    transforms.ToTensor(),
    normalize
])

valid_dataset.transform = transforms.Compose([
    transforms.Resize([70, 70]),
    transforms.ToTensor(),
    normalize
])

# Размер каждого пакета при обучение
# Training data loaders.
train_loader = DataLoader(
    train_dataset, batch_size=BATCH_SIZE,
    shuffle=True
)
# Размер каждого пакета при проверке
# Validation data loaders.
valid_loader = DataLoader(
    valid_dataset, batch_size=BATCH_SIZE,
    shuffle=False
)

# Указание на используемую модель
def google(): # pretrained=True для tensorflow
    model = models.googlenet(weights=models.GoogLeNet_Weights.IMAGENET1K_V1)
    # Добавление линейного (выходного) слоя на основании которого идет дообучение
    model.fc = torch.nn.Linear(1024, len(train_dataset.classes))
    for param in model.parameters():
        param.requires_grad = True
    # Заморозка весов т.к. при переобучении модели они должны быть постоянны, а меняться будет только последний слой
    model.inception3a.requires_grad = False
    model.inception3b.requires_grad = False
    model.inception4a.requires_grad = False
    model.inception4b.requires_grad = False
    model.inception4c.requires_grad = False
    model.inception4d.requires_grad = False
    model.inception4e.requires_grad = False
    return model

# Функция обучения модели. Epoch - количество итераций обучения (прогонов по нейросети)
def train(model, optimizer, train_loader, val_loader, epoch=10):
    loss_train, acc_train = [], []
    loss_valid, acc_valid = [], []
    # tqdm - прогресс бар
    for epoch in tqdm(range(epoch)):
        # Ошибки
        losses, equals = [], []
        torch.set_grad_enabled(True)

        # Train. Обучение. В цикле проходится по картинкам и оптимизируются потери
        model.train()
        for i, (image, target) in enumerate(train_loader):
            image = image.to(device)
            target = target.to(device)
            output = model(image)
            loss = criterion(output,target)

            losses.append(loss.item())
            equals.extend(
                [x.item() for x in torch.argmax(output, 1) == target])

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        # Метрики отображающие резултитаты обучения модели
        loss_train.append(np.mean(losses))
        acc_train.append(np.mean(equals))
        losses, equals = [], []
        torch.set_grad_enabled(False)

        # Validate. Оценка качества обучения
        model.eval()
        for i , (image, target) in enumerate(valid_loader):
            image = image.to(device)
            target = target.to(device)

            output = model(image)
            loss = criterion(output,target)

            losses.append(loss.item())
            equals.extend(
                [y.item() for y in torch.argmax(output, 1) == target])

        loss_valid.append(np.mean(losses))
        acc_valid.append(np.mean(equals))

    return loss_train, acc_train, loss_valid, acc_valid

criterion = torch.nn.CrossEntropyLoss()
criterion = criterion.to(device)

model = google() # здесь можете заменить на VGG
print('Model: GoogLeNet\n')

# оптимайзер - отвечает за поиск и подбор оптимальных весов
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
model = model.to(device)

loss_train, acc_train, loss_valid, acc_valid = train(
model, optimizer, train_loader, valid_loader, 30)
print('acc_train:', acc_train, '\nacc_valid:', acc_valid)

# Сохранение модели в текущую рабочую директорию
pkl_filename = "model/pickle_model.pkl"
with open(pkl_filename, 'wb') as file:
    pickle.dump(model, file)

