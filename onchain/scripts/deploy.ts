import { ethers } from "hardhat";

interface DeploymentResult {
  authorityRegistry: string;
  poaAnchor: string;
  anomalyRegistry: string;
  network: string;
  timestamp: number;
}

async function main() {
  console.log("🚀 Deploying Smart Grid Contracts");
  console.log("=" .repeat(60));

  const [deployer] = await ethers.getSigners();
  console.log(`📝 Deploying from: ${deployer.address}`);

  const network = await ethers.provider.getNetwork();
  const chainId = network.chainId;
  console.log(`📍 Network: ${network.name} (ChainID: ${chainId})`);

  // 1. Deploy AuthorityRegistry
  console.log("\n1️⃣  Deploying AuthorityRegistry...");
  const AuthorityRegistry = await ethers.getContractFactory("AuthorityRegistry");
  const authorityRegistry = await AuthorityRegistry.deploy();
  await authorityRegistry.waitForDeployment();
  const authorityAddr = await authorityRegistry.getAddress();
  console.log(`   ✅ AuthorityRegistry: ${authorityAddr}`);

  // 2. Deploy PoAAnchor
  console.log("\n2️⃣  Deploying PoAAnchor...");
  const PoAAnchor = await ethers.getContractFactory("PoAAnchor");
  const poaAnchor = await PoAAnchor.deploy(authorityAddr);
  await poaAnchor.waitForDeployment();
  const poaAddr = await poaAnchor.getAddress();
  console.log(`   ✅ PoAAnchor: ${poaAddr}`);

  // 3. Deploy AnomalyRegistry
  console.log("\n3️⃣  Deploying AnomalyRegistry...");
  const AnomalyRegistry = await ethers.getContractFactory("AnomalyRegistry");
  const anomalyRegistry = await AnomalyRegistry.deploy(authorityAddr);
  await anomalyRegistry.waitForDeployment();
  const anomalyAddr = await anomalyRegistry.getAddress();
  console.log(`   ✅ AnomalyRegistry: ${anomalyAddr}`);

  // 4. Register deployer as authority
  console.log("\n4️⃣  Registering deployer as authority...");
  await authorityRegistry.registerAuthority(deployer.address);
  console.log(`   ✅ Deployer registered as authority`);

  // 5. Verify contract deployment
  console.log("\n5️⃣  Verifying deployments...");
  const authCount = await authorityRegistry.authorityCount();
  const anomalyCount = await anomalyRegistry.recordCount();
  console.log(`   ✅ Authorities registered: ${authCount}`);
  console.log(`   ✅ Anomalies recorded: ${anomalyCount}`);

  // Summary
  const result: DeploymentResult = {
    authorityRegistry: authorityAddr,
    poaAnchor: poaAddr,
    anomalyRegistry: anomalyAddr,
    network: network.name,
    timestamp: Date.now(),
  };

  console.log("\n" + "=" .repeat(60));
  console.log("✨ DEPLOYMENT SUMMARY");
  console.log("=" .repeat(60));
  console.log(JSON.stringify(result, null, 2));

  // Save deployment result
  const fs = await import("fs");
  const path = await import("path");
  const deploymentDir = path.join(__dirname, "../deployments");

  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  const filename = path.join(deploymentDir, `${network.name}-${Date.now()}.json`);
  fs.writeFileSync(filename, JSON.stringify(result, null, 2));
  console.log(`\n📁 Deployment saved to: ${filename}`);

  // Export for TypeChain
  console.log("\n📦 Contract addresses for mobile app:");
  console.log(`
export const CONTRACTS = {
  authorityRegistry: '${authorityAddr}',
  poaAnchor: '${poaAddr}',
  anomalyRegistry: '${anomalyAddr}',
  network: '${network.name}',
  chainId: ${chainId},
} as const;
  `);
}

main()
  .then(() => {
    console.log("\n✅ Deployment successful!");
    process.exit(0);
  })
  .catch((error) => {
    console.error("\n❌ Deployment failed:", error);
    process.exit(1);
  });
