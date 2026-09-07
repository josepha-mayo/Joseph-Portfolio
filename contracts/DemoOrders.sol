// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;
/// @notice Fixture generator only. No money, tokens or production access control.
contract DemoOrders {
    mapping(bytes32 => bool) public seen;
    event OrderPlaced(bytes32 indexed orderId, address indexed account, uint256 units);
    function place(bytes32 orderId, uint256 units) external {
        require(!seen[orderId], "duplicate order");
        require(units > 0 && units < 1000000, "invalid units");
        seen[orderId] = true;
        emit OrderPlaced(orderId, msg.sender, units);
    }
}
