case class Record(name:String, grades:Array[Int])

object HelloWorld {
    def main(args: Array[String]) {
        val x = Record("Ken Pu", Array(1,2,3))
        println("Hello, world.")
        println(x)
        println(x.name)
        x.grades.foreach {
            println
        }
    }
}
