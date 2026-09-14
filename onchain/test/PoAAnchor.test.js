const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("PoAAnchor", function () {
  let owner, authority, stranger, authorityRegistry, poaAnchor;

  const HASH_1 = ethers.keccak256(ethers.toUtf8Bytes("poa-block-1"));
  const HASH_2 = ethers.keccak256(ethers.toUtf8Bytes("poa-block-2"));

  beforeEach(async function () {
    [owner, authority, stranger] = await ethers.getSigners();

    const AuthorityRegistry = await ethers.getContractFactory("AuthorityRegistry");
    authorityRegistry = await AuthorityRegistry.deploy(owner.address);
    await authorityRegistry.waitForDeployment();
    await authorityRegistry.addAuthority(authority.address, "Data Custodian");

    const PoAAnchor = await ethers.getContractFactory("PoAAnchor");
    poaAnchor = await PoAAnchor.deploy(await authorityRegistry.getAddress());
    await poaAnchor.waitForDeployment();
  });

  it("rejects anchoring from non-authorities", async function () {
    await expect(poaAnchor.connect(stranger).anchorBlock(1, HASH_1)).to.be.revertedWith(
      "PoAAnchor: caller is not an authority"
    );
  });

  it("anchors a block and updates lastAnchoredIndex", async function () {
    await expect(poaAnchor.connect(authority).anchorBlock(1, HASH_1))
      .to.emit(poaAnchor, "BlockAnchored")
      .withArgs(1, HASH_1, authority.address);

    expect(await poaAnchor.lastAnchoredIndex()).to.equal(1);
    expect(await poaAnchor.anchorCount()).to.equal(1);
    expect(await poaAnchor.verifyAnchor(1, HASH_1)).to.equal(true);
    expect(await poaAnchor.verifyAnchor(1, HASH_2)).to.equal(false);
  });

  it("rejects a non-increasing index", async function () {
    await poaAnchor.connect(authority).anchorBlock(5, HASH_1);
    await expect(poaAnchor.connect(authority).anchorBlock(5, HASH_2)).to.be.revertedWith(
      "PoAAnchor: index not increasing"
    );
    await expect(poaAnchor.connect(authority).anchorBlock(3, HASH_2)).to.be.revertedWith(
      "PoAAnchor: index not increasing"
    );
  });

  it("rejects an empty hash", async function () {
    await expect(poaAnchor.connect(authority).anchorBlock(1, ethers.ZeroHash)).to.be.revertedWith(
      "PoAAnchor: empty hash"
    );
  });

  it("verifyAnchor returns false for an unanchored index", async function () {
    expect(await poaAnchor.verifyAnchor(99, HASH_1)).to.equal(false);
  });
});
