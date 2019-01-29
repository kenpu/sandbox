import org.junit.*;
import static org.junit.Assert.assertEquals;

public class TestSimple {
    @Test
    public void testAdd() {
        assertEquals("Simple adder", Main.adder(1,2), 3);
    }
}
