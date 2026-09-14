import { expect } from "chai";
import { ethers } from "hardhat";
import { AnomalyRegistry, AuthorityRegistry } from "../typechain-types";

describe("AnomalyRegistry", function () {
  let anomalyRegistry: AnomalyRegistry;
  let authorityRegistry: AuthorityRegistry;
  let owner: any;
  let authority: any;
  let nonAuthority: any;

  beforeEach(async function () {
    [owner, authority, nonAuthority] = await ethers.getSigners();

    // Deploy AuthorityRegistry first
    const AuthorityRegistryFactory = await ethers.getContractFactory("AuthorityRegistry");
    authorityRegistry = await AuthorityRegistryFactory.deploy();
    await authorityRegistry.waitForDeployment();

    // Add authority
    await authorityRegistry.registerAuthority(authority.address);

    // Deploy AnomalyRegistry
    const AnomalyRegistryFactory = await ethers.getContractFactory("AnomalyRegistry");
    anomalyRegistry = await AnomalyRegistryFactory.deploy(await authorityRegistry.getAddress());
    await anomalyRegistry.waitForDeployment();
  });

  describe("recordAnomaly", function () {
    it("should record anomaly by authority", async function () {
      const meterId = "METER_001";
      const attackType = "FRAUD";
      const confidence = 9500; // 95%
      const offChainHash = ethers.id("block_hash_001");

      await expect(
        anomalyRegistry
          .connect(authority)
          .recordAnomaly(meterId, attackType, confidence, offChainHash)
      )
        .to.emit(anomalyRegistry, "AnomalyRecorded")
        .withArgs(0, meterId, attackType, confidence, offChainHash, authority.address);

      const record = await anomalyRegistry.getRecord(0);
      expect(record.meterId).to.equal(meterId);
      expect(record.attackType).to.equal(attackType);
      expect(record.confidenceBps).to.equal(confidence);
    });

    it("should reject non-authority", async function () {
      const meterId = "METER_001";
      const attackType = "FRAUD";
      const confidence = 9500;
      const offChainHash = ethers.id("block_hash_001");

      await expect(
        anomalyRegistry
          .connect(nonAuthority)
          .recordAnomaly(meterId, attackType, confidence, offChainHash)
      ).to.be.revertedWith("AnomalyRegistry: caller is not an authority");
    });

    it("should reject invalid confidence (>10000)", async function () {
      const meterId = "METER_001";
      const attackType = "FRAUD";
      const confidence = 10001;
      const offChainHash = ethers.id("block_hash_001");

      await expect(
        anomalyRegistry
          .connect(authority)
          .recordAnomaly(meterId, attackType, confidence, offChainHash)
      ).to.be.revertedWith("AnomalyRegistry: confidence out of range");
    });

    it("should reject duplicate off-chain hash", async function () {
      const meterId = "METER_001";
      const attackType = "FRAUD";
      const confidence = 9500;
      const offChainHash = ethers.id("block_hash_001");

      // First record
      await anomalyRegistry
        .connect(authority)
        .recordAnomaly(meterId, attackType, confidence, offChainHash);

      // Attempt duplicate
      await expect(
        anomalyRegistry
          .connect(authority)
          .recordAnomaly("METER_002", "DoS", 8500, offChainHash)
      ).to.be.revertedWith("AnomalyRegistry: duplicate off-chain hash");
    });
  });

  describe("getRecords", function () {
    it("should retrieve paginated records", async function () {
      const offChainHash1 = ethers.id("block_hash_001");
      const offChainHash2 = ethers.id("block_hash_002");
      const offChainHash3 = ethers.id("block_hash_003");

      // Record 3 anomalies
      await anomalyRegistry
        .connect(authority)
        .recordAnomaly("METER_001", "FRAUD", 9500, offChainHash1);
      await anomalyRegistry
        .connect(authority)
        .recordAnomaly("METER_002", "DoS", 8500, offChainHash2);
      await anomalyRegistry
        .connect(authority)
        .recordAnomaly("METER_003", "FAULT", 7500, offChainHash3);

      // Get page 0 (offset 0, limit 2)
      const page1 = await anomalyRegistry.getRecords(0, 2);
      expect(page1).to.have.lengthOf(2);
      expect(page1[0].meterId).to.equal("METER_001");
      expect(page1[1].meterId).to.equal("METER_002");

      // Get page 1 (offset 2, limit 2)
      const page2 = await anomalyRegistry.getRecords(2, 2);
      expect(page2).to.have.lengthOf(1);
      expect(page2[0].meterId).to.equal("METER_003");

      // Get beyond range
      const page3 = await anomalyRegistry.getRecords(10, 2);
      expect(page3).to.have.lengthOf(0);
    });
  });

  describe("recordCount", function () {
    it("should return correct count", async function () {
      expect(await anomalyRegistry.recordCount()).to.equal(0);

      await anomalyRegistry
        .connect(authority)
        .recordAnomaly("METER_001", "FRAUD", 9500, ethers.id("block_001"));

      expect(await anomalyRegistry.recordCount()).to.equal(1);

      await anomalyRegistry
        .connect(authority)
        .recordAnomaly("METER_002", "DoS", 8500, ethers.id("block_002"));

      expect(await anomalyRegistry.recordCount()).to.equal(2);
    });
  });
});
