// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ImageVerification {
    struct ImageData {
        string imageHash;
        string watermarkId;
        address creator;
        uint256 timestamp;
        bool exists;
    }

    mapping(string => ImageData) private images;

    function registerImage(string memory _imageHash, string memory _watermarkId) public {
        require(!images[_imageHash].exists, "Image already registered");
        images[_imageHash] = ImageData(_imageHash, _watermarkId, msg.sender, block.timestamp, true);
    }

    function verifyImage(string memory _imageHash) public view returns (bool) {
        return images[_imageHash].exists;
    }

    function getImageData(string memory _imageHash) public view returns (string memory, string memory, address, uint256, bool) {
        ImageData memory data = images[_imageHash];
        return (data.imageHash, data.watermarkId, data.creator, data.timestamp, data.exists);
    }
}
