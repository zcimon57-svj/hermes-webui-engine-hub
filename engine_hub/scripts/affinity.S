/* Linux x86_64 static, libc-free container launcher. argv[1]=CPU, argv[2]=exec. */
.global _start
.text
_start:
    mov %rsp, %r12
    cmpq $3, (%rsp)
    jl invalid
    mov 16(%rsp), %r10
    xor %ecx, %ecx
parse:
    movzbl (%r10), %eax
    test %eax, %eax
    jz parsed
    sub $48, %eax
    cmp $9, %eax
    ja invalid
    imul $10, %ecx
    add %eax, %ecx
    cmp $1023, %ecx
    ja invalid
    inc %r10
    jmp parse
parsed:
    mov %ecx, %r13d
    sub $128, %rsp
    mov %rsp, %rdi
    xor %eax, %eax
    mov $128, %ecx
    rep stosb
    bts %r13, (%rsp)
    mov $203, %eax             /* sched_setaffinity */
    xor %edi, %edi
    mov $128, %esi
    mov %rsp, %rdx
    syscall
    test %rax, %rax
    js invalid
    mov 24(%r12), %rdi
    lea 24(%r12), %rsi
    mov (%r12), %rax
    lea 16(%r12,%rax,8), %rdx /* inherited envp */
    mov $59, %eax              /* execve */
    syscall
invalid:
    mov $70, %edi
    mov $60, %eax
    syscall
.section .note.GNU-stack,"",@progbits
