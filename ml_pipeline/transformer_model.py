"""
Step 4: Transformer Autoencoder Model
Architecture: Input Embedding → Positional Encoding → Multi-Head Attention → Feedforward
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math


class PositionalEncoding(nn.Module):
    """Positional encoding for temporal sequences"""
    
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # Create positional encoding matrix
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        """
        Args:
            x: Tensor of shape [seq_len, batch_size, d_model]
        """
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)


class TransformerAutoencoder(nn.Module):
    """
    Transformer-based Autoencoder for Anomaly Detection
    
    Architecture:
    - Input Embedding
    - Positional Encoding
    - Transformer Encoder (Multi-Head Attention)
    - Decoder (reconstruction)
    
    Anomaly Detection: reconstruction_error = ||input - output||
    """
    
    def __init__(
        self,
        n_features: int,
        d_model: int = 128,
        n_heads: int = 8,
        n_encoder_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
        max_seq_length: int = 100
    ):
        super().__init__()
        
        self.n_features = n_features
        self.d_model = d_model
        
        # Input embedding: project features to d_model dimension
        self.input_embedding = nn.Linear(n_features, d_model)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, max_seq_length, dropout)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            activation='gelu',
            batch_first=False  # [seq_len, batch, features]
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=n_encoder_layers
        )
        
        # Decoder: project back to original feature space
        self.decoder = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, n_features)
        )
        
        # Store attention weights for explainability
        self.attention_weights = None
        
    def forward(self, x, return_attention=False):
        """
        Args:
            x: Input tensor [batch_size, seq_len, n_features]
            return_attention: If True, return attention weights
        
        Returns:
            reconstructed: Reconstructed input [batch_size, seq_len, n_features]
            attention_weights: (optional) Attention weights for explainability
        """
        # x shape: [batch_size, seq_len, n_features]
        batch_size, seq_len, _ = x.shape
        
        # Embed input
        embedded = self.input_embedding(x)  # [batch, seq_len, d_model]
        
        # Transpose for transformer: [seq_len, batch, d_model]
        embedded = embedded.transpose(0, 1)
        
        # Add positional encoding
        embedded = self.pos_encoder(embedded)
        
        # Transformer encoding
        if return_attention:
            # Store attention weights from last layer
            encoded = self.transformer_encoder(embedded)
            # Note: Getting attention weights requires modifying encoder
            # For now, we'll extract them in a separate method
        else:
            encoded = self.transformer_encoder(embedded)
        
        # Transpose back: [batch, seq_len, d_model]
        encoded = encoded.transpose(0, 1)
        
        # Decode to original feature space
        reconstructed = self.decoder(encoded)  # [batch, seq_len, n_features]
        
        if return_attention:
            return reconstructed, self.extract_attention_weights(x)
        
        return reconstructed
    
    def extract_attention_weights(self, x):
        """
        Extract attention weights from the last encoder layer
        This is used for explainability (Step 6)
        """
        # This is a simplified version
        # In practice, you'd need to modify TransformerEncoderLayer to return attention
        batch_size, seq_len, _ = x.shape
        
        # Placeholder: return uniform attention for now
        # In full implementation, hook into transformer layers
        attention = torch.ones(batch_size, seq_len, seq_len) / seq_len
        
        return attention
    
    def compute_reconstruction_error(self, x, reconstructed):
        """
        Compute reconstruction error for anomaly detection
        
        Returns:
            error: Mean squared error per sequence [batch_size]
        """
        # MSE per sequence
        error = torch.mean((x - reconstructed) ** 2, dim=(1, 2))
        return error


class TransformerTrainer:
    """Training loop for Transformer Autoencoder"""
    
    def __init__(
        self,
        model: TransformerAutoencoder,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    ):
        self.model = model.to(device)
        self.device = device
        self.train_losses = []
        self.val_losses = []
        
    def train_epoch(self, dataloader, optimizer, criterion):
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        
        for batch_x, _ in dataloader:
            batch_x = batch_x.to(self.device)
            
            # Forward pass
            reconstructed = self.model(batch_x)
            loss = criterion(reconstructed, batch_x)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(dataloader)
    
    def validate(self, dataloader, criterion):
        """Validate model"""
        self.model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for batch_x, _ in dataloader:
                batch_x = batch_x.to(self.device)
                reconstructed = self.model(batch_x)
                loss = criterion(reconstructed, batch_x)
                total_loss += loss.item()
        
        return total_loss / len(dataloader)
    
    def fit(
        self,
        train_loader,
        val_loader,
        epochs: int = 50,
        learning_rate: float = 0.0001,
        patience: int = 10
    ):
        """
        Train the model with early stopping
        """
        print(f"\n🚀 Training Transformer Autoencoder on {self.device}...")
        
        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=1e-5
        )
        criterion = nn.MSELoss()
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader, optimizer, criterion)
            val_loss = self.validate(val_loader, criterion)
            
            self.train_losses.append(train_loss)
            self.val_losses.append(val_loss)
            
            print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                torch.save(self.model.state_dict(), 'ml_pipeline/models/best_transformer.pth')
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"   ⏹️ Early stopping at epoch {epoch+1}")
                    break
        
        print(f"   ✅ Training complete. Best val loss: {best_val_loss:.6f}")
        
        # Load best model
        self.model.load_state_dict(torch.load('ml_pipeline/models/best_transformer.pth'))
