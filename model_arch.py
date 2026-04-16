# model_arch.py
import torch.nn as nn

class NeuralNet(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super().__init__()
        self.l1 = nn.Linear(input_size, hidden_size) # 128
        self.bn1 = nn.BatchNorm1d(hidden_size)
        self.l2 = nn.Linear(hidden_size, hidden_size // 2) # 64
        self.bn2 = nn.BatchNorm1d(hidden_size // 2)
        self.l3 = nn.Linear(hidden_size // 2, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        out = self.dropout(self.relu(self.bn1(self.l1(x))))
        out = self.dropout(self.relu(self.bn2(self.l2(out))))
        out = self.l3(out)
        return out