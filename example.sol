contract Test {
    function test(uint amount) {
        msg.sender.transfer(amount);
    }
}