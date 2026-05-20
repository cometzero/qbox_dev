/* SPDX-License-Identifier: MIT */
/*
 * Apollo Hexagon APKO negative UAPI smoke helper.
 */

#include "apollo_hexagon_uapi_guest.h"

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

#define APOLLO_HEXAGON_ACCEL_SCAN_MAX 256

static int validate_query_caps(const struct drm_apollo_hexagon_query_caps *caps)
{
	if (caps->generic_abi_version != APOLLO_HEXAGON_GENERIC_ABI_VERSION)
		return -EINVAL;
	if (!(caps->supported_executable_formats &
	      APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0_BIT))
		return -EINVAL;
	if (caps->fence_model != APOLLO_HEXAGON_FENCE_MODEL_ASYNC_IRQ_POLL)
		return -EINVAL;
	if (caps->fault_record_size != sizeof(struct drm_apollo_hexagon_fault))
		return -EINVAL;
	return 0;
}

static int open_apollo_accel(void)
{
	struct drm_apollo_hexagon_query_caps caps;
	struct drm_apollo_hexagon_query query;
	char path[64];
	int fd;
	int i;

	for (i = 0; i < APOLLO_HEXAGON_ACCEL_SCAN_MAX; i++) {
		int ret;

		ret = snprintf(path, sizeof(path), "/dev/accel/accel%d", i);
		if (ret < 0 || (size_t)ret >= sizeof(path))
			return -ENAMETOOLONG;

		fd = open(path, O_RDWR | O_CLOEXEC);
		if (fd < 0)
			continue;

		memset(&query, 0, sizeof(query));
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_QUERY, &query) == 0) {
			memset(&caps, 0, sizeof(caps));
			caps.size = sizeof(caps);
			if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_QUERY_CAPS,
				  &caps) < 0 ||
			    validate_query_caps(&caps)) {
				close(fd);
				continue;
			}
			printf("APKO negative: drm-accel device=%s queues=%u\n",
			       path, query.queue_count);
			printf("APKO negative: generic_abi_version=%u executable_formats=0x%08x fault_record_size=%u\n",
			       caps.generic_abi_version,
			       caps.supported_executable_formats,
			       caps.fault_record_size);
			return fd;
		}
		close(fd);
	}

	return -ENOENT;
}

static struct drm_apollo_hexagon_apko_header make_valid_vadd_header(void)
{
	struct drm_apollo_hexagon_apko_header header;

	memset(&header, 0, sizeof(header));
	header.magic = APOLLO_HEXAGON_APKO_MAGIC;
	header.header_bytes = sizeof(header);
	header.abi_version = APOLLO_HEXAGON_APKO_ABI_VERSION;
	header.executable_format = APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0;
	header.entry_kind = APOLLO_HEXAGON_EXEC_KIND_VADD;
	header.input_bytes = APOLLO_HEXAGON_VADD_INPUT_WORDS * sizeof(uint32_t);
	header.output_bytes = APOLLO_HEXAGON_VADD_OUTPUT_WORDS * sizeof(uint32_t);

	return header;
}

static int expect_errno(const char *name, int expected_errno, int rc)
{
	if (rc == 0) {
		fprintf(stderr, "FAIL: %s unexpectedly succeeded\n", name);
		return 1;
	}
	if (errno != expected_errno) {
		fprintf(stderr,
			"FAIL: %s returned errno=%d (%s), expected errno=%d (%s)\n",
			name, errno, strerror(errno), expected_errno,
			strerror(expected_errno));
		return 1;
	}

	printf("PASS: %s rejected errno=%s\n", name, strerror(expected_errno));
	return 0;
}

static int expect_create_reject(int fd, const char *name,
				struct drm_apollo_hexagon_apko_header header,
				int expected_errno)
{
	struct drm_apollo_hexagon_exec_create create;

	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	create.data_ptr = (uint64_t)(uintptr_t)&header;
	create.data_size = sizeof(header);

	return expect_errno(name, expected_errno,
			    ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE,
				  &create));
}

static int run_context_tests(int fd)
{
	struct drm_apollo_hexagon_context_destroy destroy;
	struct drm_apollo_hexagon_context_create create;
	int failed = 0;

	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	create.generic_abi_version = APOLLO_HEXAGON_GENERIC_ABI_VERSION + 1;
	failed |= expect_errno("bad context ABI version", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE,
				     &create));

	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	create.generic_abi_version = APOLLO_HEXAGON_GENERIC_ABI_VERSION;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE, &create) < 0) {
		fprintf(stderr, "FAIL: context create failed: %s\n",
			strerror(errno));
		return 1;
	}
	if (!create.handle || create.queue_count < 1 ||
	    create.fence_model != APOLLO_HEXAGON_FENCE_MODEL_ASYNC_IRQ_POLL) {
		fprintf(stderr, "FAIL: context create returned bad metadata\n");
		failed = 1;
	}

	memset(&destroy, 0, sizeof(destroy));
	destroy.handle = create.handle;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY, &destroy) < 0) {
		fprintf(stderr, "FAIL: context destroy failed: %s\n",
			strerror(errno));
		return 1;
	}
	printf("PASS: context create/destroy ok handle=%u queues=%u\n",
	       create.handle, create.queue_count);

	failed |= expect_errno("destroyed context handle", ENOENT,
			       ioctl(fd,
				     DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY,
				     &destroy));

	return failed;
}

static int run_bo_tests(int fd)
{
	struct drm_apollo_hexagon_bo_destroy destroy;
	struct drm_apollo_hexagon_bo_create create;
	int failed = 0;

	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	failed |= expect_errno("bad BO size", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE,
				     &create));

	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	create.bo_size = 4096;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE, &create) < 0) {
		fprintf(stderr, "FAIL: BO create failed: %s\n",
			strerror(errno));
		return 1;
	}
	if (!create.handle || create.bo_size < 4096) {
		fprintf(stderr, "FAIL: BO create returned bad metadata\n");
		failed = 1;
	}

	memset(&destroy, 0, sizeof(destroy));
	destroy.handle = create.handle;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY, &destroy) < 0) {
		fprintf(stderr, "FAIL: BO destroy failed: %s\n",
			strerror(errno));
		return 1;
	}
	printf("PASS: BO create/destroy ok handle=%u size=%llu mmap_offset=0x%llx\n",
	       create.handle, (unsigned long long)create.bo_size,
	       (unsigned long long)create.mmap_offset);

	failed |= expect_errno("destroyed BO handle", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY,
				     &destroy));

	return failed;
}

static int run_bo_bind_tests(int fd)
{
	struct drm_apollo_hexagon_context_destroy context_destroy;
	struct drm_apollo_hexagon_context_create context_create;
	struct drm_apollo_hexagon_bo_destroy bo_destroy;
	struct drm_apollo_hexagon_bo_create bo_create;
	struct drm_apollo_hexagon_bo_unbind unbind;
	struct drm_apollo_hexagon_bo_bind bind;
	int failed = 0;

	memset(&bind, 0, sizeof(bind));
	bind.context_handle = 1;
	bind.bo_handle = 1;
	bind.length = 4096;
	bind.usage = APOLLO_HEXAGON_BO_BIND_USAGE_READ;
	failed |= expect_errno("bad BO bind size", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_BIND,
				     &bind));

	memset(&bo_create, 0, sizeof(bo_create));
	bo_create.size = sizeof(bo_create);
	bo_create.bo_size = 8192;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE, &bo_create) < 0) {
		fprintf(stderr, "FAIL: BO create for bind failed: %s\n",
			strerror(errno));
		return 1;
	}

	memset(&bind, 0, sizeof(bind));
	bind.size = sizeof(bind);
	bind.context_handle = 0xdead;
	bind.bo_handle = bo_create.handle;
	bind.length = 4096;
	bind.usage = APOLLO_HEXAGON_BO_BIND_USAGE_READ;
	failed |= expect_errno("bad BO bind context", ENOENT,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_BIND,
				     &bind));

	memset(&context_create, 0, sizeof(context_create));
	context_create.size = sizeof(context_create);
	context_create.generic_abi_version = APOLLO_HEXAGON_GENERIC_ABI_VERSION;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE,
		  &context_create) < 0) {
		fprintf(stderr, "FAIL: context create for BO bind failed: %s\n",
			strerror(errno));
		failed = 1;
		goto out_destroy_bo;
	}

	memset(&bind, 0, sizeof(bind));
	bind.size = sizeof(bind);
	bind.context_handle = context_create.handle;
	bind.bo_handle = 0xdead;
	bind.length = 4096;
	bind.usage = APOLLO_HEXAGON_BO_BIND_USAGE_READ;
	failed |= expect_errno("bad BO bind handle", ENOENT,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_BIND,
				     &bind));

	memset(&bind, 0, sizeof(bind));
	bind.size = sizeof(bind);
	bind.context_handle = context_create.handle;
	bind.bo_handle = bo_create.handle;
	bind.length = 1024;
	bind.usage = APOLLO_HEXAGON_BO_BIND_USAGE_READ;
	failed |= expect_errno("unaligned BO bind length", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_BIND,
				     &bind));

	memset(&bind, 0, sizeof(bind));
	bind.size = sizeof(bind);
	bind.context_handle = context_create.handle;
	bind.bo_handle = bo_create.handle;
	bind.length = 4096;
	bind.usage = APOLLO_HEXAGON_BO_BIND_USAGE_READ |
		     APOLLO_HEXAGON_BO_BIND_USAGE_WRITE;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_BIND, &bind) < 0) {
		fprintf(stderr, "FAIL: BO bind failed: %s\n", strerror(errno));
		failed = 1;
		goto out_destroy_context;
	}
	if (!bind.bind_handle || !bind.iova) {
		fprintf(stderr, "FAIL: BO bind returned bad metadata\n");
		failed = 1;
		goto out_destroy_context;
	}

	memset(&unbind, 0, sizeof(unbind));
	unbind.context_handle = context_create.handle;
	unbind.bind_handle = bind.bind_handle;
	failed |= expect_errno("bad BO unbind size", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND,
				     &unbind));

	unbind.size = sizeof(unbind);
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND, &unbind) < 0) {
		fprintf(stderr, "FAIL: BO unbind failed: %s\n",
			strerror(errno));
		failed = 1;
	} else {
		printf("PASS: BO bind/unbind ok bind=%u bo=%u iova=0x%llx length=%llu\n",
		       bind.bind_handle, bo_create.handle,
		       (unsigned long long)bind.iova,
		       (unsigned long long)bind.length);
	}

	failed |= expect_errno("destroyed BO bind handle", ENOENT,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_UNBIND,
				     &unbind));

out_destroy_context:
	memset(&context_destroy, 0, sizeof(context_destroy));
	context_destroy.handle = context_create.handle;
	if (context_create.handle &&
	    ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY,
		  &context_destroy) < 0) {
		fprintf(stderr, "FAIL: context destroy after BO bind failed: %s\n",
			strerror(errno));
		failed = 1;
	}

out_destroy_bo:
	memset(&bo_destroy, 0, sizeof(bo_destroy));
	bo_destroy.handle = bo_create.handle;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY, &bo_destroy) < 0) {
		fprintf(stderr, "FAIL: BO destroy after bind failed: %s\n",
			strerror(errno));
		failed = 1;
	}

	return failed;
}

static int run_cmd_submit_tests(int fd)
{
	struct drm_apollo_hexagon_context_destroy context_destroy;
	struct drm_apollo_hexagon_context_create context_create;
	struct drm_apollo_hexagon_bo_destroy bo_destroy;
	struct drm_apollo_hexagon_bo_create bo_create;
	struct drm_apollo_hexagon_cmd_submit submit;
	struct drm_apollo_hexagon_fault fault;
	uint32_t *packet = MAP_FAILED;
	int failed = 0;

	memset(&submit, 0, sizeof(submit));
	submit.context_handle = 1;
	submit.command_bo_handle = 1;
	submit.command_size = APOLLO_HEXAGON_CMDQ_PACKET_BYTES;
	submit.queue_id = 1;
	failed |= expect_errno("bad command BO submit size", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT,
				     &submit));

	memset(&context_create, 0, sizeof(context_create));
	context_create.size = sizeof(context_create);
	context_create.generic_abi_version = APOLLO_HEXAGON_GENERIC_ABI_VERSION;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_CREATE,
		  &context_create) < 0) {
		fprintf(stderr, "FAIL: context create for command BO failed: %s\n",
			strerror(errno));
		return 1;
	}

	memset(&bo_create, 0, sizeof(bo_create));
	bo_create.size = sizeof(bo_create);
	bo_create.bo_size = 4096;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_CREATE, &bo_create) < 0) {
		fprintf(stderr, "FAIL: command BO create failed: %s\n",
			strerror(errno));
		failed = 1;
		goto out_destroy_context;
	}

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.context_handle = 0xdead;
	submit.command_bo_handle = bo_create.handle;
	submit.command_size = APOLLO_HEXAGON_CMDQ_PACKET_BYTES;
	submit.queue_id = 1;
	failed |= expect_errno("bad command BO submit context", ENOENT,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT,
				     &submit));

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.context_handle = context_create.handle;
	submit.command_bo_handle = 0xdead;
	submit.command_size = APOLLO_HEXAGON_CMDQ_PACKET_BYTES;
	submit.queue_id = 1;
	failed |= expect_errno("bad command BO handle", ENOENT,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT,
				     &submit));

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.context_handle = context_create.handle;
	submit.command_bo_handle = bo_create.handle;
	submit.command_size = APOLLO_HEXAGON_CMDQ_PACKET_BYTES - 4;
	submit.queue_id = 1;
	failed |= expect_errno("bad command BO size", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT,
				     &submit));

	packet = mmap(NULL, bo_create.bo_size, PROT_READ | PROT_WRITE,
		      MAP_SHARED, fd, bo_create.mmap_offset);
	if (packet == MAP_FAILED) {
		fprintf(stderr, "FAIL: command BO mmap failed: %s\n",
			strerror(errno));
		failed = 1;
		goto out_destroy_bo;
	}
	memset(packet, 0, bo_create.bo_size);
	packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_SIGNAL_FENCE;

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.context_handle = context_create.handle;
	submit.command_bo_handle = bo_create.handle;
	submit.command_size = APOLLO_HEXAGON_CMDQ_PACKET_BYTES;
	submit.queue_id = 1;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT, &submit) < 0) {
		fprintf(stderr, "FAIL: command BO submit failed: %s\n",
			strerror(errno));
		failed = 1;
	} else if (submit.status != APOLLO_HEXAGON_CMDQ_STATUS_DONE ||
		   submit.result != APOLLO_HEXAGON_CMDQ_FAULT_NONE ||
		   !submit.fence_seq) {
		fprintf(stderr, "FAIL: command BO submit returned bad status\n");
		failed = 1;
		} else {
			printf("PASS: command BO submit signal-fence ok fence=%u status=0x%x result=0x%x\n",
			       submit.fence_seq, submit.status, submit.result);
		}

		memset(packet, 0, bo_create.bo_size);
		packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_EXECUTABLE;
		packet[1] = 1;
		packet[2] = APOLLO_HEXAGON_APKO_MAGIC;
		packet[3] = APOLLO_HEXAGON_APKO_ABI_VERSION + 1;
		packet[4] = APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0;
		packet[5] = APOLLO_HEXAGON_EXEC_KIND_VADD;
		packet[6] = APOLLO_HEXAGON_VADD_INPUT_WORDS * sizeof(uint32_t);
		packet[7] = APOLLO_HEXAGON_VADD_OUTPUT_WORDS * sizeof(uint32_t);

		memset(&submit, 0, sizeof(submit));
		submit.size = sizeof(submit);
		submit.context_handle = context_create.handle;
		submit.command_bo_handle = bo_create.handle;
		submit.command_size = APOLLO_HEXAGON_CMDQ_PACKET_BYTES;
		submit.queue_id = 1;
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT, &submit) == 0) {
			fprintf(stderr,
				"FAIL: command BO bad LOAD_EXECUTABLE unexpectedly succeeded\n");
			failed = 1;
		} else if (errno != EIO) {
			fprintf(stderr,
				"FAIL: command BO bad LOAD_EXECUTABLE returned errno=%d (%s), expected errno=%d (%s)\n",
				errno, strerror(errno), EIO, strerror(EIO));
			failed = 1;
		} else if (submit.status != APOLLO_HEXAGON_CMDQ_STATUS_ERROR ||
			   submit.result != APOLLO_HEXAGON_CMDQ_FAULT_MALFORMED_PACKET ||
			   !submit.fence_seq) {
			fprintf(stderr,
				"FAIL: command BO bad LOAD_EXECUTABLE returned bad fault status=0x%x result=0x%x fence=%u\n",
				submit.status, submit.result, submit.fence_seq);
			failed = 1;
		} else {
			printf("PASS: command BO bad LOAD_EXECUTABLE fault ok fence=%u status=0x%x result=0x%x\n",
			       submit.fence_seq, submit.status, submit.result);
		}

		memset(packet, 0, bo_create.bo_size);
		packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_EXECUTABLE;
		packet[1] = 1;
		packet[2] = APOLLO_HEXAGON_APKO_MAGIC;
		packet[3] = APOLLO_HEXAGON_APKO_ABI_VERSION;
		packet[4] = APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0;
		packet[5] = APOLLO_HEXAGON_EXEC_KIND_VADD;
		packet[6] = APOLLO_HEXAGON_VADD_INPUT_WORDS * sizeof(uint32_t);
		packet[7] = APOLLO_HEXAGON_VADD_OUTPUT_WORDS * sizeof(uint32_t);
		packet += APOLLO_HEXAGON_CMDQ_PACKET_WORDS;
		packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_LOAD_PAYLOAD;
		packet[1] = 1;
		packet[2] = APOLLO_HEXAGON_APKO_PAYLOAD_MAGIC;
		packet[3] = APOLLO_HEXAGON_APKO_PAYLOAD_VERSION;
		packet[4] = APOLLO_HEXAGON_EXEC_KIND_VADD;
		packet[5] = APOLLO_HEXAGON_APKO_PAYLOAD_DESCRIPTOR_WORDS;
		packet[6] = 1;
		packet[7] = APOLLO_HEXAGON_APKO_CODE_OP_MODEL_DISPATCH |
			    APOLLO_HEXAGON_EXEC_KIND_CNN;
		packet -= APOLLO_HEXAGON_CMDQ_PACKET_WORDS;

		memset(&submit, 0, sizeof(submit));
		submit.size = sizeof(submit);
		submit.context_handle = context_create.handle;
		submit.command_bo_handle = bo_create.handle;
		submit.command_size = 2 * APOLLO_HEXAGON_CMDQ_PACKET_BYTES;
		submit.queue_id = 1;
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT, &submit) == 0) {
			fprintf(stderr,
				"FAIL: command BO bad LOAD_PAYLOAD unexpectedly succeeded\n");
			failed = 1;
		} else if (errno != EIO) {
			fprintf(stderr,
				"FAIL: command BO bad LOAD_PAYLOAD returned errno=%d (%s), expected errno=%d (%s)\n",
				errno, strerror(errno), EIO, strerror(EIO));
			failed = 1;
		} else if (submit.status != APOLLO_HEXAGON_CMDQ_STATUS_ERROR ||
			   submit.result != APOLLO_HEXAGON_CMDQ_FAULT_MALFORMED_PACKET ||
			   !submit.fence_seq) {
			fprintf(stderr,
				"FAIL: command BO bad LOAD_PAYLOAD returned bad fault status=0x%x result=0x%x fence=%u\n",
				submit.status, submit.result, submit.fence_seq);
			failed = 1;
		} else {
			printf("PASS: command BO bad LOAD_PAYLOAD fault ok fence=%u status=0x%x result=0x%x\n",
			       submit.fence_seq, submit.status, submit.result);
		}

		memset(packet, 0, bo_create.bo_size);
		packet[0] = APOLLO_HEXAGON_CMDQ_OPCODE_COPY;
		packet[2] = 0x20000000u;
		packet[4] = 0x10000000u;
		packet[6] = APOLLO_HEXAGON_CMDQ_PACKET_BYTES;

		memset(&submit, 0, sizeof(submit));
		submit.size = sizeof(submit);
		submit.context_handle = context_create.handle;
		submit.command_bo_handle = bo_create.handle;
		submit.command_size = APOLLO_HEXAGON_CMDQ_PACKET_BYTES;
		submit.queue_id = 1;
		if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CMD_SUBMIT, &submit) == 0) {
			fprintf(stderr,
				"FAIL: command BO invalid IOVA unexpectedly succeeded\n");
			failed = 1;
		} else if (errno != EIO) {
			fprintf(stderr,
				"FAIL: command BO invalid IOVA returned errno=%d (%s), expected errno=%d (%s)\n",
				errno, strerror(errno), EIO, strerror(EIO));
			failed = 1;
		} else if (submit.status != APOLLO_HEXAGON_CMDQ_STATUS_ERROR ||
			   submit.result != APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR ||
			   !submit.fence_seq) {
			fprintf(stderr,
				"FAIL: command BO invalid IOVA returned bad fault status=0x%x result=0x%x fence=%u\n",
				submit.status, submit.result, submit.fence_seq);
			failed = 1;
		} else {
			memset(&fault, 0, sizeof(fault));
			fault.size = sizeof(fault);
			fault.flags = APOLLO_HEXAGON_GET_FAULT_FLAG_CLEAR;
			if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT,
				  &fault) < 0) {
				fprintf(stderr,
					"FAIL: command BO invalid IOVA GET_FAULT failed: %s\n",
					strerror(errno));
				failed = 1;
			} else if (fault.code != APOLLO_HEXAGON_FAULT_CODE_JOB_FAILED ||
				   fault.queue_id != submit.queue_id ||
				   fault.status != APOLLO_HEXAGON_CMDQ_STATUS_ERROR ||
				   fault.result != APOLLO_HEXAGON_CMDQ_FAULT_DMA_ERROR ||
				   fault.fence_seq != submit.fence_seq) {
				fprintf(stderr,
					"FAIL: command BO invalid IOVA GET_FAULT returned bad record queue=%u code=%u status=0x%x result=0x%x fence=%u\n",
					fault.queue_id, fault.code, fault.status,
					fault.result, fault.fence_seq);
				failed = 1;
			} else {
				printf("PASS: command BO invalid IOVA fault ok queue=%u fence=%u status=0x%x result=0x%x\n",
				       fault.queue_id, fault.fence_seq,
				       fault.status, fault.result);
			}
		}

		munmap(packet, bo_create.bo_size);

out_destroy_bo:
	memset(&bo_destroy, 0, sizeof(bo_destroy));
	bo_destroy.handle = bo_create.handle;
	if (bo_create.handle &&
	    ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_BO_DESTROY, &bo_destroy) < 0) {
		fprintf(stderr, "FAIL: command BO destroy failed: %s\n",
			strerror(errno));
		failed = 1;
	}

out_destroy_context:
	memset(&context_destroy, 0, sizeof(context_destroy));
	context_destroy.handle = context_create.handle;
	if (context_create.handle &&
	    ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_CONTEXT_DESTROY,
		  &context_destroy) < 0) {
		fprintf(stderr, "FAIL: command context destroy failed: %s\n",
			strerror(errno));
		failed = 1;
	}

	return failed;
}

static int create_valid_executable(int fd, uint32_t *handle)
{
	struct drm_apollo_hexagon_apko_header header;
	struct drm_apollo_hexagon_exec_create create;

	header = make_valid_vadd_header();
	memset(&create, 0, sizeof(create));
	create.size = sizeof(create);
	create.data_ptr = (uint64_t)(uintptr_t)&header;
	create.data_size = sizeof(header);

	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_EXEC_CREATE, &create) < 0) {
		fprintf(stderr, "FAIL: valid APKO create failed: %s\n",
			strerror(errno));
		return 1;
	}
	if (!create.handle ||
	    create.executable_format != APOLLO_HEXAGON_EXEC_FORMAT_APKO_V0 ||
	    create.abi_version != APOLLO_HEXAGON_APKO_ABI_VERSION ||
	    create.entry_kind != APOLLO_HEXAGON_EXEC_KIND_VADD) {
		fprintf(stderr, "FAIL: valid APKO create returned bad metadata\n");
		return 1;
	}

	*handle = create.handle;
	return 0;
}

static int destroy_executable(int fd, uint32_t handle)
{
	struct drm_apollo_hexagon_exec_destroy destroy;

	memset(&destroy, 0, sizeof(destroy));
	destroy.handle = handle;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_EXEC_DESTROY, &destroy) < 0) {
		fprintf(stderr, "FAIL: APKO destroy failed: %s\n", strerror(errno));
		return 1;
	}
	return 0;
}

static int expect_submit_reject(int fd, const char *name,
				struct drm_apollo_hexagon_submit submit,
				int expected_errno)
{
	return expect_errno(name, expected_errno,
			    ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_SUBMIT, &submit));
}

static int run_wait_tests(int fd)
{
	uint32_t input[APOLLO_HEXAGON_VADD_INPUT_WORDS] = {
		1, 2, 3, 4,
		10, 20, 30, 40,
	};
	uint32_t output[APOLLO_HEXAGON_VADD_OUTPUT_WORDS] = { 0 };
	struct drm_apollo_hexagon_submit submit;
	struct drm_apollo_hexagon_wait wait;
	uint32_t handle;
	int failed = 0;

	if (create_valid_executable(fd, &handle))
		return 1;

	memset(&wait, 0, sizeof(wait));
	wait.fence_seq = 1;
	failed |= expect_errno("bad WAIT size", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_WAIT, &wait));

	memset(&wait, 0, sizeof(wait));
	wait.size = sizeof(wait);
	failed |= expect_errno("zero WAIT fence", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_WAIT, &wait));

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.executable_handle = handle;
	submit.queue_id = 1;
	submit.input_ptr = (uint64_t)(uintptr_t)input;
	submit.output_ptr = (uint64_t)(uintptr_t)output;
	submit.input_bytes = sizeof(input);
	submit.output_bytes = sizeof(output);
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_SUBMIT, &submit) < 0) {
		fprintf(stderr, "FAIL: valid APKO submit for WAIT failed: %s\n",
			strerror(errno));
		failed = 1;
		goto out_destroy;
	}
	if (!submit.fence_seq) {
		fprintf(stderr, "FAIL: valid APKO submit returned zero fence\n");
		failed = 1;
		goto out_destroy;
	}

	memset(&wait, 0, sizeof(wait));
	wait.size = sizeof(wait);
	wait.queue_id = 7;
	wait.fence_seq = submit.fence_seq;
	failed |= expect_errno("bad WAIT queue", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_WAIT, &wait));

	memset(&wait, 0, sizeof(wait));
	wait.size = sizeof(wait);
	wait.queue_id = submit.queue_id;
	wait.fence_seq = submit.fence_seq;
	if (ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_WAIT, &wait) < 0) {
		fprintf(stderr, "FAIL: WAIT completed fence failed: %s\n",
			strerror(errno));
		failed = 1;
	} else {
		printf("PASS: WAIT completed fence=%u current=%u status=0x%x result=0x%x\n",
		       submit.fence_seq, wait.current_fence_seq, wait.status,
		       wait.result);
	}

	memset(&wait, 0, sizeof(wait));
	wait.size = sizeof(wait);
	wait.queue_id = submit.queue_id;
	wait.fence_seq = submit.fence_seq + 1;
	if (wait.fence_seq)
		failed |= expect_errno("future WAIT fence", ETIMEDOUT,
				       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_WAIT,
					     &wait));

out_destroy:
	if (destroy_executable(fd, handle))
		failed = 1;

	return failed;
}

static int run_submit_negative_tests(int fd)
{
	uint32_t input[APOLLO_HEXAGON_VADD_INPUT_WORDS] = {
		0x3f800000, 0x40000000, 0x40400000, 0x40800000,
		0x41200000, 0x41a00000, 0x41f00000, 0x42200000,
	};
	struct drm_apollo_hexagon_fault fault;
	uint32_t output[APOLLO_HEXAGON_VADD_OUTPUT_WORDS] = { 0 };
	struct drm_apollo_hexagon_submit submit;
	uint32_t handle;
	int failed = 0;

	if (create_valid_executable(fd, &handle))
		return 1;

	memset(&submit, 0, sizeof(submit));
	submit.size = sizeof(submit);
	submit.executable_handle = handle;
	submit.queue_id = 1;
	submit.input_ptr = (uint64_t)(uintptr_t)input;
	submit.output_ptr = (uint64_t)(uintptr_t)output;
	submit.input_bytes = sizeof(input) - 1;
	submit.output_bytes = sizeof(output);
	failed |= expect_submit_reject(fd, "wrong input byte count", submit,
				       EINVAL);

	submit.input_bytes = sizeof(input);
	submit.output_bytes = sizeof(output) - 1;
	failed |= expect_submit_reject(fd, "wrong output byte count", submit,
				       EINVAL);

	submit.output_bytes = sizeof(output);
	submit.queue_id = 7;
	failed |= expect_submit_reject(fd, "wrong queue id", submit, EINVAL);

	submit.queue_id = 1;
	submit.input_ptr = 1;
	failed |= expect_submit_reject(fd, "invalid input pointer", submit,
				       EFAULT);

	if (destroy_executable(fd, handle))
		failed = 1;

	submit.input_ptr = (uint64_t)(uintptr_t)input;
	failed |= expect_submit_reject(fd, "destroyed executable handle", submit,
				       ENOENT);

	memset(&fault, 0, sizeof(fault));
	fault.size = sizeof(fault);
	failed |= expect_errno("empty fault record", ENODATA,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT,
				     &fault));

	memset(&fault, 0, sizeof(fault));
	fault.size = sizeof(fault) - 4;
	failed |= expect_errno("bad fault request size", EINVAL,
			       ioctl(fd, DRM_IOCTL_APOLLO_HEXAGON_GET_FAULT,
				     &fault));

	return failed;
}

int main(void)
{
	struct drm_apollo_hexagon_apko_header header;
	int failed = 0;
	int fd;

	fd = open_apollo_accel();
	if (fd < 0) {
		fprintf(stderr, "FAIL: failed to open Apollo DRM accel device: %s\n",
			strerror(-fd));
		return 1;
	}

	header = make_valid_vadd_header();
	header.magic = 0;
	failed |= expect_create_reject(fd, "bad APKO magic", header, EINVAL);

	header = make_valid_vadd_header();
	header.abi_version = APOLLO_HEXAGON_APKO_ABI_VERSION + 1;
	failed |= expect_create_reject(fd, "bad APKO ABI version", header,
				       EINVAL);

	header = make_valid_vadd_header();
	header.entry_kind = 99;
	failed |= expect_create_reject(fd, "bad APKO entry kind", header,
				       EINVAL);

	header = make_valid_vadd_header();
	header.input_bytes -= 4;
	failed |= expect_create_reject(fd, "bad APKO input byte count", header,
				       EINVAL);

	header = make_valid_vadd_header();
	header.reserved[0] = 1;
	failed |= expect_create_reject(fd, "nonzero APKO reserved field", header,
				       EINVAL);

	failed |= run_context_tests(fd);
	failed |= run_bo_tests(fd);
	failed |= run_bo_bind_tests(fd);
	failed |= run_cmd_submit_tests(fd);
	failed |= run_wait_tests(fd);
	failed |= run_submit_negative_tests(fd);
	close(fd);

	if (failed)
		return 1;

	printf("PASS: APKO negative ioctl coverage completed\n");
	return 0;
}
