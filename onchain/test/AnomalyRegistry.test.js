const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AnomalyRegistry", function () {
  let owner, authority, stranger, authorityRegistry, anomalyRegistry;

  const HASH_1 = ethers.keccak256(ethers.toUtf8Bytes("poa-block-1"));
  const HASH_2 = ethers.keccak256(ethers.toUtf8Bytes("poa-block-2"));

  beforeEach(async function () {
    [owner, authority, stranger] = await ethers.getSigners();

    const AuthorityRegistry = await ethers.getContractFactory("AuthorityRegistry");
    authorityRegistry = await AuthorityRegistry.deploy(owner.address);
    await authorityRegistry.waitForDeployment();
    await authorityRegistry.addAuthority(authority.address, "Security Auditor");

    const AnomalyRegistry = await ethers.getContractFactory("AnomalyRegistry");
    anomalyRegistry = await AnomalyRegistry.deploy(await authorityRegistry.getAddress());
    await anomalyRegistry.waitForDeployment();
  });

  it("rejects submissions from non-authorities", async function () {
    await expect(
      anomalyRegistry.connect(stranger).recordAnomaly("SM_01", "fdia", 8000, HASH_1)
    ).to.be.revertedWith("AnomalyRegistry: caller is not an authority");
  });

  it("records an anomaly from a registered authority", async function () {
    await expect(anomalyRegistry.connect(authority).recordAnomaly("SM_01", "fdia", 8000, HASH_1))
      .to.emit(anomalyRegistry, "AnomalyRecorded")
      .withArgs(0, "SM_01", "fdia", 8000, HASH_1, authority.address);

    expect(await anomalyRegistry.recordCount()).to.equal(1);
    const record = await anomalyRegistry.getRecord(0);
    expect(record.meterId).to.equal("SM_01");
    expect(record.attackType).to.equal("fdia");
    expect(record.confidenceBps).to.equal(8000);
    expect(record.offChainBlockHash).to.equal(HASH_1);
    expect(record.reportedBy).to.equal(authority.address);
  });

  it("rejects confidence above 100%", async function () {
    await expect(
      anomalyRegistry.connect(authority).recordAnomaly("SM_01", "fdia", 10001, HASH_1)
    ).to.be.revertedWith("AnomalyRegistry: confidence out of range");
  });

  it("rejects a duplicate off-chain block hash", async function () {
    await anomalyRegistry.connect(authority).recordAnomaly("SM_01", "fdia", 8000, HASH_1);
    await expect(
      anomalyRegistry.connect(authority).recordAnomaly("SM_02", "dos", 7000, HASH_1)
    ).to.be.revertedWith("AnomalyRegistry: duplicate off-chain hash");
  });

  it("paginates records", async function () {
    await anomalyRegistry.connect(authority).recordAnomaly("SM_01", "fdia", 8000, HASH_1);
    await anomalyRegistry.connect(authority).recordAnomaly("SM_02", "dos", 7000, HASH_2);

    const page = await anomalyRegistry.getRecords(0, 1);
    expect(page.length).to.equal(1);
    expect(page[0].meterId).to.equal("SM_01");

    const page2 = await anomalyRegistry.getRecords(1, 10);
    expect(page2.length).to.equal(1);
    expect(page2[0].meterId).to.equal("SM_02");

    const emptyPage = await anomalyRegistry.getRecords(5, 10);
    expect(emptyPage.length).to.equal(0);
  });
});
