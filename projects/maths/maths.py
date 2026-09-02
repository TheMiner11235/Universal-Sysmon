import numpy as np
import pyopencl as cl

def gpu_crunch_fibonacci():
    # 1. Set up the OpenCL environment for your AMD GPU
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)
    
    # 2. Define the size of our search grid (10,000 x 10,000 = 100 Million combinations!)
    # This searches seed numbers from 0 to 9,999
    grid_size = 10000
    
    # 3. Create the data arrays
    # Row indices represent Seed X, Column indices represent Seed Y
    x_seeds = np.repeat(np.arange(grid_size, dtype=np.int32), grid_size)
    y_seeds = np.tile(np.arange(grid_size, dtype=np.int32), grid_size)
    output_results = np.zeros(grid_size * grid_size, dtype=np.int32)
    
    # 4. Move the data from system RAM to your 7600 XT VRAM
    mf = cl.mem_flags
    x_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=x_seeds)
    y_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=y_seeds)
    out_buf = cl.Buffer(ctx, mf.WRITE_ONLY, output_results.nbytes)
    
    # 5. OpenCL Kernel Code (This runs on thousands of GPU cores at once)
    # It checks the 5-step rule: 2x + 3y == 100
    kernel_code = """
    __kernel void check_fib(__global const int* x, __global const int* y, __global int* out) {
        int i = get_global_id(0);
        if ((2 * x[i]) + (3 * y[i]) == 100) {
            out[i] = 1; // Mark as a valid solution
        } else {
            out[i] = 0;
        }
    }
    """
    
    # Compile the code for your specific AMD architecture
    prg = cl.Program(ctx, kernel_code).build()
    
    # Execute the code across all 100 million combinations instantly
    prg.check_fib(queue, (grid_size * grid_size,), None, x_buf, y_buf, out_buf)
    
    # Pull the answers back from the GPU to your CPU/RAM
    cl.enqueue_copy(queue, output_results, out_buf)
    
    # 6. Find where the GPU found matches and print them
    match_indices = np.where(output_results == 1)[0]
    
    print(f"GPU finished scanning {grid_size * grid_size:,} combinations.")
    print(f"{'Seed 1 (x)':<12}{'Seed 2 (y)':<12}{'Full 5-Step Sequence'}")
    print("-" * 50)
    
    for idx in match_indices:
        x_val = x_seeds[idx]
        y_val = y_seeds[idx]
        print(f"{x_val:<12}{y_val:<12}{x_val} -> {y_val} -> {x_val+y_val} -> {x_val+2*y_val} -> 100")

if __name__ == "__main__":
    gpu_crunch_fibonacci()
