package myobj;

public class Hello {
    public int f1 = 123;
    public int f2;
    public static double pi = 3.1415;
    public Hello(int i) {
        this.f2 = i;
    }
    public void print() {
        System.out.printf("I am: (%f, %d, %d)\n", pi, f1, f2);
    }
    public static void Pi() {
        System.out.println("Pi = " + pi);
    }
}
