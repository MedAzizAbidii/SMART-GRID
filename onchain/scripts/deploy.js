const fs = require("fs");
const path = require("path");
const { ethers, network } = require("hardhat");

// Mirrors the 4 off-chain PoA authorities (blockchain/poa_ledger.py) so the
// on-chain registry has the same governance set from day one. The deployer
// wallet is also registered as an authority so it can submit a smoke-test
// anomaly record right after deployment.
const AUTHORITY_LABELS = ["Utility Operator", "Grid Supervisor", "Security Auditor", "Data Custodian"];

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log(`Deploying with account: ${deployer.address}`);
  console.log(`Network: ${network.name}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`Deployer balance: ${ethers.formatEther(balance)} ETH`);
  if (balance === 0n && network.name !== "hardhat") {
    throw new Error(
      `Deployer wallet ${deployer.address} has 0 ETH on ${network.name}. Fund it via a faucet before deploying.`
    );
  }

  const AuthorityRegistry = await ethers.getContractFactory("AuthorityRegistry");
  const authorityRegistry = await AuthorityRegistry.deploy(deployer.address);
  await authorityRegistry.waitForDeployment();
  const authorityRegistryAddress = await authorityRegistry.getAddress();
  console.log(`AuthorityRegistry deployed to: ${authorityRegistryAddress}`);

  const addTx = await authorityRegistry.addAuthority(deployer.address, AUTHORITY_LABELS[0]);
  await addTx.wait();
  console.log(`Registered deployer as authority ("${AUTHORITY_LABELS[0]}")`);

  const AnomalyRegistry = await ethers.getContractFactory("AnomalyRegistry");
  const anomalyRegistry = await AnomalyRegistry.deploy(authorityRegistryAddress);
  await anomalyRegistry.waitForDeployment();
  const anomalyRegistryAddress = await anomalyRegistry.getAddress();
  console.log(`AnomalyRegistry deployed to: ${anomalyRegistryAddress}`);

  const PoAAnchor = await ethers.getContractFactory("PoAAnchor");
  const poaAnchor = await PoAAnchor.deploy(authorityRegistryAddress);
  await poaAnchor.waitForDeployment();
  const poaAnchorAddress = await poaAnchor.getAddress();
  console.log(`PoAAnchor deployed to: ${poaAnchorAddress}`);

  const deploymentRecord = {
    network: network.name,
    chainId: Number((await ethers.provider.getNetwork()).chainId),
    deployer: deployer.address,
    deployedAt: new Date().toISOString(),
    contracts: {
      AuthorityRegistry: authorityRegistryAddress,
      AnomalyRegistry: anomalyRegistryAddress,
      PoAAnchor: poaAnchorAddress,
    },
  };

  const deploymentsDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(deploymentsDir, { recursive: true });
  const outFile = path.join(deploymentsDir, `${network.name}.json`);
  fs.writeFileSync(outFile, JSON.stringify(deploymentRecord, null, 2));
  console.log(`\nDeployment record written to ${outFile}`);

  // Also drop a copy the Python backend can read directly without a
  // separate build step (production/blockchain/onchain_bridge.py).
  const backendCopyDir = path.join(__dirname, "..", "..", "production", "security");
  fs.mkdirSync(backendCopyDir, { recursive: true });
  fs.writeFileSync(
    path.join(backendCopyDir, `onchain_deployment_${network.name}.json`),
    JSON.stringify(deploymentRecord, null, 2)
  );

  console.log("\nDone. Set these in your backend environment to enable the on-chain bridge:");
  console.log(`  SGRID_ONCHAIN_ENABLED=1`);
  console.log(`  SGRID_ONCHAIN_NETWORK=${network.name}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
