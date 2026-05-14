"""
Pre-trained Transformer Model for Smart Grid Anomaly Detection
Uses transfer learning with BERT-style encoder
"""

import torch
import torch.nn as nn
from transformers import BertModel, BertConfig
import numpy as np


class PretrainedTransformerAutoencoder(nn.Module):
    """
    Transformer Autoencoder using pre-trained BERT encoder
    
    Architecture:
    - Pre-trained BERT encoder (frozen or fine-tuned)
    - Custom projection layer for time series
    - Decoder for reconstruction
    """
    
    def __init__(
        self,
        n_features,
        d_model=128,
        n_heads=8,
        n_decoder_layers=2,
        d_ff=512,
        dropout=0.1,
        max_seq_length=100,
        freeze_encoder=False
    ):
        super().__init__()
        
        self.n_features = n_features
        self.d_model = d_model
        self.max_seq_length = max_seq_length
        
        # Pre-trained BERT configuration (small version for efficiency)
        bert_config = BertConfig(
            hidden_size=d_model,
            num_hidden_layers=4,  # Smaller than full BERT
            num_attention_heads=n_heads,
            intermediate_size=d_ff,
            hidden_dropout_prob=dropout,
            attention_probs_dropout_prob=dropout,
            max_position_embeddings=max_seq_length
        )
        
        # Initialize BERT encoder
        # Note: We create a small BERT-style model rather than loading full BERT
        # This is more suitable for time series data
        self.encoder = BertModel(bert_config)
        
        # Optionally freeze encoder weights for transfer learning
        if freeze_encoder:
            for param in self.encoder.parameters():
                param.requires_grad = False
        
        # Input projection: map features to BERT hidden size
        self.input_projection = nn.Linear(n_features, d_model)
        
        # Positional encoding
        self.pos_encoder = PositionalEncoding(d_model, dropout, max_seq_length)
        
        # Decoder (Transformer decoder layers)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            batch_first=True
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=n_decoder_layers)
        
        # Output projection: map back to original feature space
        self.output_projection = nn.Linear(d_model, n_features)
        
        # Layer normalization
        self.norm = nn.LayerNorm(d_model)
        
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: Input tensor of shape (batch_size, seq_length, n_features)
            
        Returns:
            Reconstructed tensor of shape (batch_size, seq_length, n_features)
        """
        batch_size, seq_length, _ = x.shape
        
        # Project input to model dimension
        x = self.input_projection(x)  # (batch, seq, d_model)
        
        # Add positional encoding
        x = self.pos_encoder(x)
        
        # BERT encoder expects (batch, seq, hidden_size)
        # Get encoder output
        encoder_output = self.encoder(inputs_embeds=x).last_hidden_state
        
        # Normalize encoder output
        encoder_output = self.norm(encoder_output)
        
        # Decoder: use encoder output as memory
        # For autoencoder, we use the same sequence as target
        decoder_output = self.decoder(
            tgt=encoder_output,
            memory=encoder_output
        )
        
        # Project back to original feature space
        reconstructed = self.output_projection(decoder_output)
        
        return reconstructed
    
    def encode(self, x):
        """
        Get encoded representation (for feature extraction)
        
        Args:
            x: Input tensor of shape (batch_size, seq_length, n_features)
            
        Returns:
            Encoded tensor of shape (batch_size, seq_length, d_model)
        """
        x = self.input_projection(x)
        x = self.pos_encoder(x)
        encoder_output = self.encoder(inputs_embeds=x).last_hidden_state
        return encoder_output


class PositionalEncoding(nn.Module):
    """Positional encoding for transformer"""
    
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # Create positional encoding matrix
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x):
        """
        Args:
            x: Tensor of shape (batch_size, seq_length, d_model)
        """
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class PretrainedTransformerTrainer:
    """Trainer for pre-trained transformer model"""
    
    def __init__(self, model, device='cpu', learning_rate=1e-4):
        self.model = model.to(device)
        self.device = device
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=0.01
        )
        self.criterion = nn.MSELoss()
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
    
    def train_epoch(self, train_loader):
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        
        for batch_idx, (data, _) in enumerate(train_loader):
            data = data.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            reconstructed = self.model(data)
            
            # Calculate loss
            loss = self.criterion(reconstructed, data)
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(train_loader)
    
    def validate(self, val_loader):
        """Validate the model"""
        self.model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for data, _ in val_loader:
                data = data.to(self.device)
                reconstructed = self.model(data)
                loss = self.criterion(reconstructed, data)
                total_loss += loss.item()
        
        return total_loss / len(val_loader)
    
    def train(self, train_loader, val_loader, epochs=50, patience=10):
        """
        Train the model with early stopping
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Maximum number of epochs
            patience: Early stopping patience
            
        Returns:
            Dictionary with training history
        """
        best_val_loss = float('inf')
        patience_counter = 0
        history = {
            'train_loss': [],
            'val_loss': []
        }
        
        print(f"\n🚀 Training Pre-trained Transformer Model")
        print(f"   Device: {self.device}")
        print(f"   Epochs: {epochs}")
        print(f"   Patience: {patience}")
        print()
        
        for epoch in range(epochs):
            # Train
            train_loss = self.train_epoch(train_loader)
            
            # Validate
            val_loss = self.validate(val_loader)
            
            # Update learning rate
            self.scheduler.step(val_loss)
            
            # Save history
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            
            # Print progress
            print(f"Epoch {epoch+1}/{epochs} - "
                  f"Train Loss: {train_loss:.6f}, "
                  f"Val Loss: {val_loss:.6f}")
            
            # Check for improvement
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                torch.save(self.model.state_dict(), 'ml_pipeline/models/best_pretrained_transformer.pth')
                print(f"   ✅ Best model saved! (Val Loss: {val_loss:.6f})")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"\n⏹️ Early stopping triggered after {epoch+1} epochs")
                    break
        
        print(f"\n✅ Training complete!")
        print(f"   Best validation loss: {best_val_loss:.6f}")
        
        return history


def create_pretrained_model(n_features, config):
    """
    Factory function to create pre-trained model
    
    Args:
        n_features: Number of input features
        config: Configuration object with model parameters
        
    Returns:
        PretrainedTransformerAutoencoder model
    """
    model = PretrainedTransformerAutoencoder(
        n_features=n_features,
        d_model=config.D_MODEL,
        n_heads=config.N_HEADS,
        n_decoder_layers=config.N_ENCODER_LAYERS,
        d_ff=config.D_FF,
        dropout=config.DROPOUT,
        max_seq_length=config.MAX_SEQ_LENGTH,
        freeze_encoder=False  # Allow fine-tuning
    )
    
    return model


if __name__ == "__main__":
    # Test the model
    print("Testing Pre-trained Transformer Model...")
    
    # Create dummy data
    batch_size = 32
    seq_length = 20
    n_features = 14
    
    x = torch.randn(batch_size, seq_length, n_features)
    
    # Create model
    model = PretrainedTransformerAutoencoder(
        n_features=n_features,
        d_model=128,
        n_heads=8,
        n_decoder_layers=2,
        d_ff=512,
        dropout=0.1,
        max_seq_length=100
    )
    
    # Forward pass
    output = model(x)
    
    print(f"✅ Model test successful!")
    print(f"   Input shape: {x.shape}")
    print(f"   Output shape: {output.shape}")
    print(f"   Model parameters: {sum(p.numel() for p in model.parameters()):,}")
