class Main {
    public static int adder(int... args) {
        int sum = 0;
        for(int i : args) {
            sum += i;
        }
        return sum;
    }
}
