const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AuthorityRegistry", function () {
  let owner, alice, bob, registry;

  beforeEach(async function () {
    [owner, alice, bob] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("AuthorityRegistry");
    registry = await Registry.deploy(owner.address);
    await registry.waitForDeployment();
  });

  it("sets the deployer as owner", async function () {
    expect(await registry.owner()).to.equal(owner.address);
  });

  it("lets the owner add an authority", async function () {
    await expect(registry.addAuthority(alice.address, "Utility Operator"))
      .to.emit(registry, "AuthorityAdded")
      .withArgs(alice.address, "Utility Operator");
    expect(await registry.isAuthority(alice.address)).to.equal(true);
    expect(await registry.label(alice.address)).to.equal("Utility Operator");
  });

  it("rejects non-owner attempts to add an authority", async function () {
    await expect(registry.connect(alice).addAuthority(bob.address, "Rogue")).to.be.revertedWith(
      "AuthorityRegistry: caller is not owner"
    );
  });

  it("rejects duplicate registration", async function () {
    await registry.addAuthority(alice.address, "Utility Operator");
    await expect(registry.addAuthority(alice.address, "Utility Operator")).to.be.revertedWith(
      "AuthorityRegistry: already registered"
    );
  });

  it("lets the owner remove an authority", async function () {
    await registry.addAuthority(alice.address, "Utility Operator");
    await expect(registry.removeAuthority(alice.address)).to.emit(registry, "AuthorityRemoved").withArgs(alice.address);
    expect(await registry.isAuthority(alice.address)).to.equal(false);
  });

  it("transfers ownership", async function () {
    await registry.transferOwnership(alice.address);
    expect(await registry.owner()).to.equal(alice.address);
    await expect(registry.connect(owner).addAuthority(bob.address, "x")).to.be.revertedWith(
      "AuthorityRegistry: caller is not owner"
    );
  });

  it("tracks the full authority list including removed members", async function () {
    await registry.addAuthority(alice.address, "Utility Operator");
    await registry.addAuthority(bob.address, "Grid Supervisor");
    await registry.removeAuthority(alice.address);
    const list = await registry.authorityList();
    expect(list).to.deep.equal([alice.address, bob.address]);
    expect(await registry.authorityCount()).to.equal(2);
  });
});
