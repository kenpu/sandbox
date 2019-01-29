import org.junit.*;
import static org.junit.Assert.assertEquals;

public class TestHidden {
    @Test
    public void testAdd() {
        int[] numbers = new int[100];
        int sum = 0;
        for(int i=0; i < 100; i++) {
            numbers[i] = i;
            sum += i;
        }
        sum += 1;
        assertEquals("Hidden adder", 
                Main.adder(numbers), sum);
    }
}
