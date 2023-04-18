from ZymbitKeyringInterface import ZymbitKeyringInterface
import zymkey
from web3 import Web3

class EthAccount():
    def __init__(self, path: str, address: str, slot: int) -> None:
        self.path = path
        self.address = address
        self.slot = slot

    def __repr__(self) -> str:
        return f"Path: {self.path}, Address: {self.address}, Slot: {self.slot}"

class ZymbitEthKeyring(ZymbitKeyringInterface):
    type: str = "ETH"
    path: str = "m/44'/60'/0'/0"

    def __init__(self, options: dict = {}) -> None:
        super().__init__(options)

    def serialize(self) -> dict:
        serializedKeyring = {
            "walletName": self.walletName,
            "masterSlot": self.masterSlot
        }
        return serializedKeyring

    def deserialize(self, options: dict = {}) -> None:
        if ("walletName" not in options and "masterSlot" not in options):
            raise KeyError("walletName and masterSlot properties missing from options")

        if("walletName" in options):
            try:
                self.masterSlot: int = zymkey.client.get_wallet_key_slot('m', options["walletName"])
                self.walletName: str = options["walletName"]
            except:
                raise ValueError("Invalid walletName")
        else:
            try:
                (path, walletName, masterSlot) = zymkey.client.get_wallet_node_addr(options["masterSlot"])
                if (path == "m"):
                    self.masterSlot: int = options["masterSlot"]
                    self.walletName: str = walletName
                else:
                    raise
            except:
                raise ValueError("Invalid masterSlot")

        self.baseSlot: int = 0
        self.accounts: list[EthAccount] = []
        deepestPath: dict = {"path": "m", "slot": self.masterSlot}

        slots: list = zymkey.client.get_slot_alloc_list()[0]
        slots = list(filter(lambda slot: slot > 15, slots))

        for slot in slots:
            (path, walletName, masterSlot) = zymkey.client.get_wallet_node_addr(slot)
            if (walletName == self.walletName):
                if (path == self.path):
                    self.baseSlot = slot
                elif ((self.path + "/") in path and masterSlot == self.masterSlot):
                    self.accounts.append(EthAccount(path, self._generateEthAddress(slot), slot))
                elif (path in self.path and len(path) > len(deepestPath["path"])):
                    deepestPath = {"path": path, "slot": slot}
        
        if(self.baseSlot == 0):
            self.baseSlot = self._generateBasePathKey(deepestPath)
            
        return

    def addAccounts(self, n: int = 1) -> list[dict]:
        newAccounts = []
        if(n < 1):
            return newAccounts
        
        for i in range(n):
            newAccountIndex = self._findNextAccountIndex()
            slot = zymkey.client.gen_wallet_child_key(self.baseSlot, newAccountIndex, False)
            newAccount = EthAccount(self.path + "/" + str(newAccountIndex), self._generateEthAddress(slot), slot)
            newAccounts.append(newAccount)
            self.accounts.append(newAccount)
        
        return newAccounts
        
    def addAccount(self, index: int = 0) -> dict:
        if(index < 0):
            raise ValueError("Invalid Index")

        for account in self.accounts:
            if(account.path == self.path + "/" + str(index)):
                raise ValueError("Account already exists in keyring")
        
        slot = zymkey.client.gen_wallet_child_key(self.baseSlot, index, False)
        newAccount = EthAccount(self.path + "/" + str(index), self._generateEthAddress(slot), slot)
        self.accounts.append(newAccount)
        return newAccount
    
    def getAccounts(self) -> list[dict]:
        return self.accounts

    def removeAccount(self, address: str = None, slot: int = None, path: int = None) -> bool:
        return super().removeAccount(address, slot, path)    

    def _generateBasePathKey(self, deepestPath) -> int:
        slot = 0
        if deepestPath["path"] == "m":
            slot = zymkey.client.gen_wallet_child_key(deepestPath["slot"], 44, True)
        elif deepestPath["path"] == "m/44'":
            slot = zymkey.client.gen_wallet_child_key(deepestPath["slot"], 60, True)
        elif deepestPath["path"] == "m/44'/60'":
            slot = zymkey.client.gen_wallet_child_key(deepestPath["slot"], 0, True)
        elif deepestPath["path"] == "m/44'/60'/0'":
            slot = zymkey.client.gen_wallet_child_key(deepestPath["slot"], 0, False)
        elif deepestPath["path"] == self.path:
            return deepestPath["slot"]
        (path, walletName, masterSlot) = zymkey.client.get_wallet_node_addr(slot)
        return self._generateBasePathKey({"path": path, "slot": slot})
    
    def _findNextAccountIndex(self) -> int:
        nextAccountIndex = 0
        for account in self.accounts:
            if (int(account.path[len(self.path + "/"):]) == nextAccountIndex):
                nextAccountIndex += 1
        return nextAccountIndex
    
    def _generateEthAddress(self, slot: int) -> str:
        publicKey = zymkey.client.get_public_key(slot)
        keccakHash = Web3.keccak(bytes(publicKey)).hex()
        return Web3.toChecksumAddress(keccakHash[-40:])
    
    def __repr__(self) -> str:
        return f"ZymbitEthKeyring(type={self.type}, path={self.path}, walletName={self.walletName}, masterSlot={self.masterSlot}, baseSlot={self.baseSlot}, accounts={self.accounts})"