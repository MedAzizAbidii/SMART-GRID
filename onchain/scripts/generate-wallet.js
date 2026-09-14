// Generates a fresh Ethereum keypair locally (nothing sent over the
// network). Use this as the Sepolia deployer/authority wallet instead of
// reusing any wallet that holds real funds. Fund the printed address via
// a Sepolia faucet, then put the private key in onchain/.env
// (DEPLOYER_PRIVATE_KEY) — never commit it or paste it in chat.
const { ethers } = require("ethers");

const wallet = ethers.Wallet.createRandom();

console.log("New deployer/authority wallet generated:");
console.log("  Address:     ", wallet.address);
console.log("  Private key: ", wallet.privateKey);
console.log("  Mnemonic:    ", wallet.mnemonic.phrase);
console.log("");
console.log("Next steps:");
console.log("  1. Fund this address with Sepolia test ETH via a faucet");
console.log("     (e.g. https://sepoliafaucet.com or https://www.alchemy.com/faucets/ethereum-sepolia)");
console.log("  2. Copy the private key into onchain/.env as DEPLOYER_PRIVATE_KEY");
console.log("  3. Never commit .env or share this private key");
